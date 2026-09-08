from __future__ import annotations

import argparse
import html
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import requests


BASE_URL = "https://www.nutrime.co.kr"
USER_AGENT = "MoongCheapResearch/1.0 (internal HFF Model 1 pilot)"
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


def clean(value: str) -> str:
    value = html.unescape(value or "")
    value = TAG_RE.sub(" ", value)
    return SPACE_RE.sub(" ", value).strip()


def remove_author_fragment(value: str) -> str:
    return re.sub(r"\b[\w가-힣.-]+\*{2,}\b", "", value).strip()


def extract_cards(body: str) -> list[dict[str, str]]:
    starts = [match.start() for match in re.finditer(r'<ul class="tbody', body)]
    cards: list[dict[str, str]] = []
    for index, start in enumerate(starts):
        block = body[start : starts[index + 1] if index + 1 < len(starts) else len(body)]
        seq_match = re.search(r'board_seq="([^"]+)"', block)
        product_match = re.search(r'<a href="(/goods/view\?no=([^"]+))"[^>]*>(.*?)</a>', block, re.S)
        title_match = re.search(r'<div class="title">.*?<span[^>]*>(.*?)</span>', block, re.S)
        if not seq_match:
            continue
        cards.append(
            {
                "source_review_id": seq_match.group(1),
                "source_product_id": product_match.group(2) if product_match else "",
                "product_name": remove_author_fragment(clean(product_match.group(3))) if product_match else "",
                "review_title": clean(title_match.group(1)) if title_match else "",
                "detail_url": f"{BASE_URL}/board/view?{urlencode({'id': 'goods_review', 'seq': seq_match.group(1)})}",
            }
        )
    return cards


def extract_detail(body: str) -> dict[str, str]:
    plain = clean(re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", body, flags=re.I))
    product_match = re.search(r'<div id="goodsview"[\s\S]*?<div class="name"><a[^>]*>(.*?)</a>', body, flags=re.I)
    date_match = re.search(r"등록일 (\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2}:\d{2})?)", plain)
    title_match = re.search(r'<div class="board_detail_title">([\s\S]*?)</div>', body, flags=re.I)
    text_match = re.search(r'<div class="board_detail_contents">([\s\S]*?)</div>', body, flags=re.I)
    score_values = re.findall(r'<img[^>]*title="([1-5])"[^>]*>', body, flags=re.I)
    return {
        "review_title": clean(title_match.group(1)) if title_match else "",
        "review_text": clean(text_match.group(1)) if text_match else "",
        "review_date": date_match.group(1) if date_match else "",
        "rating": int(score_values[0]) if score_values else None,
        "detail_product_name": clean(product_match.group(1)) if product_match else "",
    }


def run_pilot(output: Path, limit: int = 100, delay_seconds: float = 0.5) -> dict[str, object]:
    if not 1 <= limit <= 100:
        raise ValueError("Pilot limit must be between 1 and 100")
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    page = 1
    stop_reason = "LIMIT_REACHED"
    previous_page_ids: set[str] = set()
    retrieved_at = datetime.now(timezone.utc).isoformat()
    while len(rows) < limit and page <= 100:
        list_url = f"{BASE_URL}/board/?{urlencode({'id': 'goods_review', 'page': page})}"
        response = session.get(list_url, timeout=20)
        if response.status_code in (403, 429):
            stop_reason = f"STOP_HTTP_{response.status_code}"
            break
        response.raise_for_status()
        cards = extract_cards(response.text)
        if not cards:
            stop_reason = "NO_PUBLIC_REVIEW_CARD"
            break
        page_ids = {card["source_review_id"] for card in cards}
        if page_ids and page_ids <= previous_page_ids:
            stop_reason = "NO_NEW_REVIEW_PAGE"
            break
        previous_page_ids.update(page_ids)
        for card in cards:
            if len(rows) >= limit or card["source_review_id"] in seen:
                continue
            detail = session.get(card["detail_url"], timeout=20)
            if detail.status_code in (403, 429):
                stop_reason = f"STOP_HTTP_{detail.status_code}"
                break
            detail.raise_for_status()
            if re.search(r"captcha|cloudflare|challenge", detail.text, flags=re.I):
                stop_reason = "STOP_CHALLENGE"
                break
            values = extract_detail(detail.text)
            rows.append(
                {
                    "source_id": "nutrime",
                    "source_review_id": card["source_review_id"],
                    "source_product_id": card["source_product_id"],
                    "product_name": values["detail_product_name"] or card["product_name"],
                    "review_title": values.get("review_title") or card["review_title"],
                    "review_text": values["review_text"],
                    "rating": values.get("rating"),
                    "review_date": values["review_date"],
                    "verified_purchase": None,
                    "verification_basis": None,
                    "source_url": card["detail_url"],
                    "retrieved_at": retrieved_at,
                }
            )
            seen.add(card["source_review_id"])
            time.sleep(delay_seconds)
        if stop_reason.startswith("STOP_"):
            break
        # The board uses an offset-like page parameter (links expose 10, 20, ...).
        page += 10
        time.sleep(delay_seconds)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    mapped = sum(bool(row["source_product_id"]) for row in rows)
    return {
        "status": "COMPLETED" if rows else "FAILED",
        "source": "nutrime",
        "rows": len(rows),
        "product_mapped_rows": mapped,
        "product_mapping_rate": mapped / len(rows) if rows else 0.0,
        "usable_review_text_rows": sum(bool(row["review_text"]) for row in rows),
        "stop_reason": stop_reason,
        "output": str(output),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/raw/reviews/nutrime/nutrime_review_pilot_100.jsonl"))
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--delay", type=float, default=0.5)
    args = parser.parse_args()
    print(json.dumps(run_pilot(args.output, args.limit, args.delay), ensure_ascii=False))
