import re
import requests
import os
from dotenv import load_dotenv

load_dotenv()

WALLET_PATTERN = re.compile(r'0x[a-fA-F0-9]{40}')

def parse_pr_url(pr_url: str) -> tuple[str, str, int]:
    parts = pr_url.strip("/").split("/")
    owner = parts[-4]
    repo = parts[-3]
    pr_number = int(parts[-1])
    return owner, repo, pr_number

def _github_headers() -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    if os.getenv("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.getenv('GITHUB_TOKEN')}"
    return headers

def verify_pr_merged(pr_url: str) -> dict:
    try:
        owner, repo, pr_number = parse_pr_url(pr_url)
    except Exception:
        return {"success": False, "error": "Invalid PR URL format"}

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    resp = requests.get(url, headers=_github_headers())

    if resp.status_code == 404:
        return {"success": False, "error": "PR not found"}
    if resp.status_code != 200:
        return {"success": False, "error": f"GitHub API error: {resp.status_code}"}

    data = resp.json()
    return {
        "success": True,
        "merged": data.get("merged", False),
        "title": data.get("title", ""),
        "author": data.get("user", {}).get("login", ""),
        "merged_at": data.get("merged_at"),
        "repo": f"{owner}/{repo}",
        "pr_number": pr_number,
    }

def get_author_wallet(pr_url: str, author: str) -> dict:
    """
    Scan PR comments for a wallet address posted by the PR author themselves.
    Author must comment: @bountyclaim 0x...
    This binds GitHub identity to wallet — only the author can claim.
    """
    try:
        owner, repo, pr_number = parse_pr_url(pr_url)
    except Exception:
        return {"success": False, "error": "Invalid PR URL format"}

    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
    resp = requests.get(url, headers=_github_headers())

    if resp.status_code != 200:
        return {"success": False, "error": f"Could not read PR comments: {resp.status_code}"}

    for comment in resp.json():
        commenter = comment.get("user", {}).get("login", "")
        body = comment.get("body", "")

        # Only accept comments from the PR author
        if commenter.lower() != author.lower():
            continue

        # Must contain @bountyclaim trigger
        if "@bountyclaim" not in body.lower():
            continue

        match = WALLET_PATTERN.search(body)
        if match:
            return {"success": True, "wallet": match.group(0), "commenter": commenter}

    return {
        "success": False,
        "error": f"No wallet found. PR author @{author} must comment: @bountyclaim 0xYourWallet"
    }
