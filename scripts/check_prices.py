#!/usr/bin/env python3
"""
Price checker for deals-tracker.

Reads products.yaml, fetches current Amazon prices via PA API 5,
and marks deals stale when price has shifted by more than STALE_THRESHOLD.

Only writes back three fields per product:
  last_checked   ISO 8601 timestamp
  stale          True when price diverges beyond threshold; False when it recovers
  current_price  Latest price from Amazon

PA API credentials (set as env vars or GitHub Actions secrets):
  AMAZON_ACCESS_KEY   AWS access key
  AMAZON_SECRET_KEY   AWS secret key
  AMAZON_PARTNER_TAG  Associates partner tag (e.g. "mytag-20")

Without credentials, the script still runs: it updates last_checked for all
products and prints a notice, but skips price comparison.
"""

import hashlib
import hmac
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml

PRODUCTS_FILE = Path(__file__).parent.parent / "products.yaml"
STALE_THRESHOLD = float(os.getenv("STALE_THRESHOLD", "0.10"))

_PA_HOST = "webservices.amazon.com"
_PA_ENDPOINT = f"https://{_PA_HOST}/paapi5/getitems"
_PA_REGION = "us-east-1"
_PA_SERVICE = "ProductAdvertisingAPI"


def _sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode(), digestmod=hashlib.sha256).digest()


def _signing_key(secret: str, date_stamp: str) -> bytes:
    k = _sign(f"AWS4{secret}".encode(), date_stamp)
    k = _sign(k, _PA_REGION)
    k = _sign(k, _PA_SERVICE)
    return _sign(k, "aws4_request")


def fetch_price(asin: str, access_key: str, secret_key: str, partner_tag: str) -> float | None:
    now = datetime.now(timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")

    body = json.dumps({
        "ItemIds": [asin],
        "Resources": ["Offers.Listings.Price"],
        "PartnerTag": partner_tag,
        "PartnerType": "Associates",
        "Marketplace": "www.amazon.com",
    })
    body_hash = hashlib.sha256(body.encode()).hexdigest()

    canonical_headers_map = {
        "content-encoding": "amz-1.0",
        "content-type": "application/json; charset=utf-8",
        "host": _PA_HOST,
        "x-amz-date": amz_date,
        "x-amz-target": "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.GetItems",
    }
    canonical_headers = "".join(f"{k}:{v}\n" for k, v in sorted(canonical_headers_map.items()))
    signed_headers = ";".join(sorted(canonical_headers_map))

    canonical_request = "\n".join([
        "POST", "/paapi5/getitems", "",
        canonical_headers, signed_headers, body_hash,
    ])

    credential_scope = f"{date_stamp}/{_PA_REGION}/{_PA_SERVICE}/aws4_request"
    string_to_sign = "\n".join([
        "AWS4-HMAC-SHA256", amz_date, credential_scope,
        hashlib.sha256(canonical_request.encode()).hexdigest(),
    ])

    sig = hmac.new(
        _signing_key(secret_key, date_stamp),
        string_to_sign.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()

    headers = {
        **canonical_headers_map,
        "Authorization": (
            f"AWS4-HMAC-SHA256 Credential={access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={sig}"
        ),
    }

    try:
        resp = requests.post(_PA_ENDPOINT, headers=headers, data=body, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("ItemsResult", {}).get("Items", [])
        listings = items[0].get("Offers", {}).get("Listings", []) if items else []
        return float(listings[0]["Price"]["Amount"]) if listings else None
    except Exception as exc:
        print(f"  PA API error for {asin}: {exc}", file=sys.stderr)
        return None


def main() -> None:
    access_key = os.getenv("AMAZON_ACCESS_KEY", "")
    secret_key = os.getenv("AMAZON_SECRET_KEY", "")
    partner_tag = os.getenv("AMAZON_PARTNER_TAG", "")
    has_credentials = bool(access_key and secret_key and partner_tag)

    if not has_credentials:
        print("PA API credentials not configured — updating timestamps only.")
        print("Set AMAZON_ACCESS_KEY, AMAZON_SECRET_KEY, AMAZON_PARTNER_TAG to enable price checks.")

    with open(PRODUCTS_FILE) as f:
        products = yaml.safe_load(f) or []

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    stale_names: list[str] = []

    for product in products:
        name = product["name"]
        asin = product.get("asin", "")
        print(f"Checking: {name}")
        product["last_checked"] = now_iso

        if not has_credentials or not asin:
            continue

        current = fetch_price(asin, access_key, secret_key, partner_tag)
        if current is None:
            print("  Could not fetch price — leaving stale flag unchanged.")
            continue

        product["current_price"] = current
        reference = float(product.get("deal_price", 0))

        if reference and abs(current - reference) / reference > STALE_THRESHOLD:
            product["stale"] = True
            stale_names.append(f"{name} (was ${reference:.2f}, now ${current:.2f})")
            print(f"  STALE: ${reference:.2f} -> ${current:.2f}")
        else:
            product["stale"] = False
            print(f"  OK: ${current:.2f}")

    with open(PRODUCTS_FILE, "w") as f:
        yaml.dump(products, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    if stale_names:
        summary = "\n".join(f"  - {s}" for s in stale_names)
        print(f"\n{len(stale_names)} deal(s) went stale:\n{summary}")
        # Expose count to GitHub Actions for downstream steps
        if gh_env := os.getenv("GITHUB_ENV"):
            with open(gh_env, "a") as f:
                f.write(f"STALE_COUNT={len(stale_names)}\n")
    else:
        print("\nAll deals OK.")


if __name__ == "__main__":
    main()
