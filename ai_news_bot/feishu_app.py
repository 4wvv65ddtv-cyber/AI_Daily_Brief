"""Send Feishu interactive cards to a user via Open Platform (personal DM)."""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional, Tuple

import requests

from ai_news_bot.config import (
    FEISHU_APP_ID,
    FEISHU_APP_SECRET,
    FEISHU_RECEIVE_ID,
    FEISHU_RECEIVE_ID_TYPE,
    FEISHU_USER_EMAIL,
    REQUEST_TIMEOUT,
)

_TOKEN_CACHE: Dict[str, Any] = {"token": "", "expire_at": 0}


def _api_ok(body: Dict[str, Any]) -> bool:
    return body.get("code") == 0


def get_tenant_access_token() -> str:
    """Fetch and cache tenant_access_token."""
    now = time.time()
    if _TOKEN_CACHE["token"] and now < _TOKEN_CACHE["expire_at"] - 60:
        return _TOKEN_CACHE["token"]

    if not FEISHU_APP_ID or not FEISHU_APP_SECRET:
        raise ValueError("FEISHU_APP_ID and FEISHU_APP_SECRET are required for personal push")

    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(
        url,
        json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET},
        timeout=REQUEST_TIMEOUT,
    )
    body = resp.json()
    if not _api_ok(body):
        raise RuntimeError(f"Failed to get tenant token: {body}")

    token = body["tenant_access_token"]
    expire = int(body.get("expire", 7200))
    _TOKEN_CACHE["token"] = token
    _TOKEN_CACHE["expire_at"] = now + expire
    return token


def resolve_receive_id() -> Tuple[str, str]:
    """
    Return (receive_id, receive_id_type).
    Uses FEISHU_RECEIVE_ID if set; otherwise looks up by FEISHU_USER_EMAIL.
    """
    if FEISHU_RECEIVE_ID:
        return FEISHU_RECEIVE_ID, FEISHU_RECEIVE_ID_TYPE

    if not FEISHU_USER_EMAIL:
        raise ValueError(
            "Set FEISHU_RECEIVE_ID (your open_id) or FEISHU_USER_EMAIL in .env"
        )

    open_id = lookup_open_id_by_email(FEISHU_USER_EMAIL)
    return open_id, "open_id"


def lookup_open_id_by_email(email: str) -> str:
    """Resolve user open_id from enterprise email."""
    token = get_tenant_access_token()
    url = "https://open.feishu.cn/open-apis/contact/v3/users/batch_get_id"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"user_id_type": "open_id"}
    resp = requests.post(
        url,
        headers=headers,
        params=params,
        json={"emails": [email]},
        timeout=REQUEST_TIMEOUT,
    )
    body = resp.json()
    if not _api_ok(body):
        raise RuntimeError(f"Failed to lookup user by email: {body}")

    users = body.get("data", {}).get("user_list", [])
    if not users or not users[0].get("user_id"):
        raise RuntimeError(
            f"No user found for email {email}. Check app permission contact:user.email:readonly"
        )
    return users[0]["user_id"]


def send_card_to_user(card: Dict[str, Any]) -> bool:
    """Send interactive card to personal Feishu via im/v1/messages."""
    receive_id, id_type = resolve_receive_id()
    token = get_tenant_access_token()

    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    params = {"receive_id_type": id_type}
    payload = {
        "receive_id": receive_id,
        "msg_type": "interactive",
        "content": json.dumps(card, ensure_ascii=False),
    }

    print(f"[feishu] Sending card to user ({id_type})...")
    resp = requests.post(
        url,
        headers=headers,
        params=params,
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )
    body = resp.json()
    if resp.status_code == 200 and _api_ok(body):
        print("[feishu] Personal message sent successfully")
        return True

    print(f"[feishu] Personal send failed: {resp.status_code} {body}")
    return False
