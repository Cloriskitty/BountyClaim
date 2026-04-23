from flask import Flask, request, jsonify
from verify_pr import verify_pr_merged, get_author_wallet
from pay import send_usdc_payment

app = Flask(__name__, static_folder="frontend", static_url_path="")

@app.route("/")
def index():
    return app.send_static_file("index.html")

@app.route("/api/claim", methods=["POST"])
def claim():
    data = request.json
    pr_url = data.get("pr_url", "").strip()
    amount = float(data.get("amount", 10.0))
    chain = data.get("chain", "base")

    if not pr_url:
        return jsonify({"success": False, "error": "Missing PR URL"}), 400

    # Step 1: Verify PR is merged
    pr_result = verify_pr_merged(pr_url)
    if not pr_result["success"]:
        return jsonify(pr_result), 400

    if not pr_result["merged"]:
        return jsonify({
            "success": False,
            "error": f"PR #{pr_result['pr_number']} is not merged yet.",
            "pr_info": pr_result,
        }), 400

    # Step 2: Find wallet address from PR author's own comment
    wallet_result = get_author_wallet(pr_url, pr_result["author"])
    if not wallet_result["success"]:
        return jsonify({
            "success": False,
            "error": wallet_result["error"],
            "pr_info": pr_result,
        }), 400

    wallet_address = wallet_result["wallet"]

    # Step 3: Send payment
    memo = f"Bounty for {pr_result['repo']}#{pr_result['pr_number']} by @{pr_result['author']}"
    pay_result = send_usdc_payment(wallet_address, amount, memo, chain)

    return jsonify({
        "success": pay_result["success"],
        "pr_info": pr_result,
        "wallet": wallet_address,
        "payment": pay_result,
    })

if __name__ == "__main__":
    app.run(debug=True, port=5001)
