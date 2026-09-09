import argparse
import json
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from enb_daily_feed import fetch_homepage, find_today_stories, get_target_date

# Collector-only bridge for the Outlook roundrobin. The legacy Brevo sender is untouched.
PERTH = ZoneInfo("Australia/Perth")
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-AU,en;q=0.9",
    "Cache-Control": "no-cache",
}


def parse_datetime(value):
    if not value:
        return None
    value = str(value).strip()
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    return dt.astimezone(PERTH)


def iter_jsonld(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from iter_jsonld(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_jsonld(child)


def authoritative_date_published(url):
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    # Prefer structured article metadata explicitly labelled datePublished.
    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.get_text("", strip=True)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        for node in iter_jsonld(data):
            published = parse_datetime(node.get("datePublished"))
            if published:
                return published, "json-ld datePublished"

    # Equivalent authoritative publication metadata fallbacks.
    for attrs in (
        {"property": "article:published_time"},
        {"name": "article:published_time"},
        {"name": "datePublished"},
        {"itemprop": "datePublished"},
    ):
        tag = soup.find("meta", attrs=attrs)
        if tag:
            published = parse_datetime(tag.get("content"))
            if published:
                return published, "published-time metadata"

    for tag in soup.find_all("time", datetime=True):
        marker = " ".join(tag.get("class", [])) + " " + (tag.get("itemprop") or "")
        marker = marker.lower()
        if "publish" in marker or "datepublished" in marker:
            published = parse_datetime(tag.get("datetime"))
            if published:
                return published, "published time element"

    return None, None


def collect():
    now = datetime.now(PERTH)
    target_date = get_target_date()
    html = fetch_homepage()
    candidates = find_today_stories(html, target_date)

    # Keep the legacy collector's deliberate ordering rule.
    candidates.sort(
        key=lambda story: story["headline"].strip().lower() == "news in brief"
    )

    cutoff = datetime.combine(now.date(), time(13, 30), tzinfo=PERTH)
    audit_end = min(now, cutoff)

    included = []
    unresolved = []
    excluded = []

    seen_urls = set()
    seen_titles = set()

    for story in candidates:
        url = story["url"].strip()
        title = story["headline"].strip()
        normalized_title = " ".join(title.lower().split())
        if not url or url in seen_urls or normalized_title in seen_titles:
            continue
        seen_urls.add(url)
        seen_titles.add(normalized_title)

        try:
            published, source = authoritative_date_published(url)
        except Exception as exc:
            unresolved.append({
                **story,
                "reason": f"article metadata fetch failed: {type(exc).__name__}: {exc}",
            })
            continue

        if not published:
            unresolved.append({
                **story,
                "reason": "authoritative original publication timestamp not found",
            })
            continue

        audited = {
            **story,
            "datePublished": published.isoformat(),
            "publication_metadata_source": source,
        }

        if published.date() != now.date():
            audited["reason"] = "original publication date is not today in Australia/Perth"
            excluded.append(audited)
            continue

        if published > audit_end:
            audited["reason"] = "original publication time is after this collector run/cutoff"
            excluded.append(audited)
            continue

        included.append(audited)

    status = "complete" if not unresolved else "incomplete"
    return {
        "schema_version": 1,
        "collector": "legacy ENB homepage date-card parser + authoritative datePublished audit",
        "generated_at": now.isoformat(),
        "timezone": "Australia/Perth",
        "target_date": now.date().isoformat(),
        "reporting_window_start": datetime.combine(now.date(), time(0, 0), tzinfo=PERTH).isoformat(),
        "reporting_window_end": cutoff.isoformat(),
        "audit_through": audit_end.isoformat(),
        "homepage_candidates": len(candidates),
        "status": status,
        "stories": included,
        "unresolved": unresolved,
        "excluded": excluded,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="roundrobin/latest.json")
    args = parser.parse_args()

    snapshot = collect()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps(snapshot, indent=2, ensure_ascii=False))

    # Do not convert an incomplete metadata audit into a false success.
    if snapshot["status"] != "complete":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
