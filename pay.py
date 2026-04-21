import requests
import hmac
import hashlib
import base64
import json
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account

load_dotenv()

OKX_API_KEY = os.getenv("OKX_API_KEY")
OKX_SECRET_KEY = os.getenv("OKX_SECRET_KEY")
OKX_PASSPHRASE = os.getenv("OKX_PASSPHRASE")
OKX_PROJECT_ID = os.getenv("OK_PROJECT_ID")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
OKX_BASE_URL = "https://web3.okx.com"

CHAIN_INDEX = "8453"  # Base mainnet
CHAIN_ID = 8453
USDC_CONTRACT = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
USDC_DECIMALS = 6

ERC20_ABI = [{
    "name": "transfer",
    "type": "function",
    "inputs": [
        {"name": "_to", "type": "address"},
        {"name": "_value", "type": "uint256"}
    ],
    "outputs": [{"name": "", "type": "bool"}]
}]

def _timestamp():
    now = datetime.now(timezone.utc)
    return now.strftime('%Y-%m-%dT%H:%M:%S.') + f"{now.microsecond // 1000:03d}Z"

def _sign(timestamp, method, path, body=""):
    message = timestamp + method.upper() + path + body
    mac = hmac.new(OKX_SECRET_KEY.encode(), message.encode(), hashlib.sha256)
    return base64.b64encode(mac.digest()).decode()

def _headers(method, path, body=""):
    ts = _timestamp()
    return {
        "OK-ACCESS-KEY": OKX_API_KEY,
        "OK-ACCESS-SIGN": _sign(ts, method, path, body),
        "OK-ACCESS-TIMESTAMP": ts,
        "OK-ACCESS-PASSPHRASE": OKX_PASSPHRASE,
        "OK-ACCESS-PROJECT": OKX_PROJECT_ID,
        "Content-Type": "application/json",
    }

def _get_sign_info(from_addr, to_addr, call_data):
    """Step 1: Ask OKX Onchain OS for gas price and nonce."""
    path = "/api/v5/wallet/pre-transaction/sign-info"
    body = json.dumps({
        "chainIndex": CHAIN_INDEX,
        "fromAddr": from_addr,
        "toAddr": to_addr,
        "txAmount": "0",
        "extJson": {"inputData": call_data},
    })
    resp = requests.post(OKX_BASE_URL + path, headers=_headers("POST", path, body), data=body)
    data = resp.json()
    if data.get("code") != "0" or not data.get("data"):
        raise RuntimeError(f"sign-info failed: {data.get('msg')}")
    return data["data"][0]

def _broadcast(signed_tx_hex):
    """Step 3: Broadcast signed transaction to Base via public RPC."""
    resp = requests.post("https://mainnet.base.org", json={
        "jsonrpc": "2.0",
        "method": "eth_sendRawTransaction",
        "params": [signed_tx_hex],
        "id": 1,
    })
    data = resp.json()
    if "error" in data:
        return {"code": "1", "msg": data["error"].get("message", "Broadcast failed")}
    return {"code": "0", "data": {"orderId": data.get("result", "")}}

def send_usdc_payment(recipient_address: str, amount_usdc: float, memo: str = "") -> dict:
    """
    Hybrid flow:
      1. OKX sign-info  → get gas + nonce (Onchain OS)
      2. web3.py        → sign transaction locally with private key
      3. OKX broadcast  → submit to Base via Onchain OS
    """
    if not PRIVATE_KEY:
        return {"success": False, "error": "PRIVATE_KEY not set in .env"}

    w3 = Web3()
    account = Account.from_key(PRIVATE_KEY)
    from_addr = account.address

    # Build ERC20 transfer calldata
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(USDC_CONTRACT),
        abi=ERC20_ABI
    )
    amount_raw = int(amount_usdc * 10 ** USDC_DECIMALS)
    call_data = contract.encode_abi(
        "transfer",
        args=[Web3.to_checksum_address(recipient_address), amount_raw]
    )

    # Step 1: OKX Onchain OS — get gas info
    try:
        sign_info = _get_sign_info(from_addr, USDC_CONTRACT, call_data)
    except RuntimeError as e:
        return {"success": False, "error": str(e)}

    nonce = int(sign_info.get("nonce", 0))
    eip1559 = sign_info.get("gasPrice", {}).get("eip1559Protocol", {})
    max_fee = int(eip1559.get("baseFee", 0)) + int(eip1559.get("proposePriorityFee", 0))
    max_priority_fee = int(eip1559.get("proposePriorityFee", 1500000))
    gas_limit = int(sign_info.get("gasLimit", 100000))

    # Step 2: web3.py — sign locally
    tx = {
        "chainId": CHAIN_ID,
        "nonce": nonce,
        "to": Web3.to_checksum_address(USDC_CONTRACT),
        "value": 0,
        "gas": gas_limit,
        "maxFeePerGas": max_fee,
        "maxPriorityFeePerGas": max_priority_fee,
        "data": call_data,
        "type": 2,
    }
    signed = account.sign_transaction(tx)
    signed_hex = "0x" + signed.raw_transaction.hex()

    # Step 3: OKX Onchain OS — broadcast
    result = _broadcast(signed_hex)
    if result.get("code") == "0":
        tx_hash = result.get("data", {}).get("orderId", signed.hash.hex())
        return {
            "success": True,
            "tx_hash": tx_hash,
            "amount": amount_usdc,
            "recipient": recipient_address,
        }
    else:
        return {
            "success": False,
            "error": result.get("msg", "Broadcast failed"),
            "detail": result,
        }
