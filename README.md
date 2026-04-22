# BountyClaim

> Open-source contribution → verified → USDC in your wallet. Instantly.


## The Problem

Open-source bounty platforms today rely on manual review at every step — maintainers
verify completion by hand, hunters chase payment over email or Discord, and transfers
go through PayPal or bank wires that take days, charge 5–10% in fees, and often get
blocked entirely. The work is done. The settlement layer is broken.

## The Solution

BountyClaim automates the last mile of open-source bounty settlement:

1. PR author comments `@bountyclaim 0xYourWallet` on their merged PR
2. Agent verifies PR is merged via GitHub API
3. Agent reads wallet address — only accepts comments from the PR author
4. OKX Onchain OS + Base sends USDC to the verified wallet
5. Done in < 30 seconds. No bank needed.

## How to Claim

As the PR author, comment on your merged PR:
```
@bountyclaim 0xYourWalletAddress
```
Then submit the PR link at the BountyClaim interface. The agent verifies your
identity from your own comment — no one else can claim on your behalf.

## Onchain OS Integration

- **OKX sign-info API** — fetches gas parameters and nonce from Onchain OS
- **Local signing** — transaction signed with wallet private key
- **Base mainnet** — USDC settlement on Base
- **Roadmap** — X Layer support and OKX native wallet integration planned

## Setup

```bash
git clone https://github.com/Cloriskitty/BountyClaim
cd BountyClaim
pip install -r requirements.txt
# Create .env with the following:
# OKX_API_KEY=
# OKX_SECRET_KEY=
# OKX_PASSPHRASE=
# OK_PROJECT_ID=
# GITHUB_TOKEN=
# PRIVATE_KEY=
python main.py
```

Open http://localhost:5001

## Demo

[Link to demo video]

## Known Limitations & Roadmap

| Issue | Status | Plan |
|---|---|---|
| Duplicate claims — same PR can be claimed multiple times | Known | Add DB to record paid PRs |
| Comment can be edited after payment | Known | Lock on first valid comment |
| Private key in .env | Dev only | HSM / KMS for production |
| OKX native wallet | Blocked (region/MPC setup) | Contact OKX team to unlock |
| X Layer support | Not yet | Next integration target |

## Built With

- Python + Flask
- OKX Onchain OS API (sign-info)
- GitHub REST API
- Base mainnet (USDC)
- web3.py
