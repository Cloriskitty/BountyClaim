# BountyClaim

> Open-source contribution → verified → USDC in your wallet. Instantly.

## The Problem

Open-source bounty tasks range from a small doc fix to a $5,000 smart contract audit.
What they all have in common: after the PR gets merged, payment stalls.

Platforms today rely on manual review at every step — maintainers verify completion
by hand, hunters chase payment over email or Discord, and transfers go through PayPal
or bank wires that take days, charge 5–10% in fees, and often get blocked entirely.

The higher the bounty, the worse the pain. A hunter who just spent a week finding a
critical security vulnerability shouldn't have to spend another week chasing a wire
transfer. The work is done. The settlement layer is broken.

## The Solution

BountyClaim automates the last mile of open-source bounty settlement:

1. PR author comments `@bountyclaim 0xYourWallet` on their merged PR
2. Agent verifies PR is merged via GitHub API
3. Agent reads wallet address — only accepts comments from the PR author
4. OKX Onchain OS broadcasts USDC payment via v6 API to Base or X Layer
5. Done in < 30 seconds. No bank needed.

## How to Claim

As the PR author, comment on your merged PR:
```
@bountyclaim 0xYourWalletAddress
```
Then submit the PR link at the BountyClaim interface. The agent verifies your
identity from your own comment — no one else can claim on your behalf.

## Onchain OS Integration

- **OKX sign-info API (v5)** — fetches gas parameters and nonce from Onchain OS
- **Local signing** — transaction signed with wallet private key
- **OKX broadcast-transaction API (v6)** — submits signed transaction via Onchain OS
- **Base mainnet** — USDC settlement (`0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`)
- **X Layer** — USDC settlement (`0x74b7F16337b8972027F6196A17a631aC6dE26d22`)
- **Roadmap** — OKX native wallet integration, duplicate-claim prevention

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

Youtube: https://youtu.be/UD8bZRZXuKg

## Known Limitations & Roadmap

| Issue | Status | Plan |
|---|---|---|
| Duplicate claims — same PR can be claimed multiple times | Known | Add DB to record paid PRs |
| Comment can be edited after payment | Known | Lock on first valid comment |
| Private key in .env | Dev only | HSM / KMS for production |
| OKX native wallet | In progress | Working with OKX team |
| X Layer support | ✅ Done | Live — select X Layer in UI |

## Built With

- Python + Flask
- OKX Onchain OS API (sign-info v5 + broadcast v6)
- GitHub REST API
- Base mainnet + X Layer (USDC)
- web3.py
