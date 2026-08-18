from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


ENB_HOMEPAGE = "https://www.energynewsbulletin.net/"
PERTH_TIMEZONE = ZoneInfo("Australia/Perth")


def clean_text(value):
    if not value:
        return ""
    return " ".join(value.split())


def get_target_date():
    now = datetime.now(PERTH_TIMEZONE)
    return now.strftime("%-d %B %Y") if not __import__("sys").platform.startswith("win") else now.strftime("%#d %B %Y")


def fetch_homepage():
    print("Opening ENB homepage...")

    headers = {
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

    response = requests.get(
        ENB_HOMEPAGE,
        headers=headers,
        timeout=30,
    )

    print(f"HTTP status: {response.status_code}")
    print(f"Homepage HTML size: {len(response.text):,} characters")

    response.raise_for_status()

    return response.text


def find_story_container(element):
    current = element

    for _ in range(8):
        if current is None:
            break

        if getattr(current, "name", None) in {
            "article",
            "li",
            "section",
            "div",
        }:
            links = current.find_all("a", href=True)

            if links:
                for link in links:
                    href = link.get("href", "")
                    if href and href != "#" and not href.startswith("javascript:"):
                        return current

        current = current.parent

    return element.parent


def extract_headline(container):
    for selector in [
        "h1",
        "h2",
        "h3",
        "h4",
        ".headline",
        ".title",
        ".card-title",
        "[class*='headline']",
        "[class*='title']",
    ]:
        element = container.select_one(selector)

        if element:
            text = clean_text(element.get_text(" ", strip=True))
            if text:
                return text

    links = container.find_all("a", href=True)

    for link in links:
        text = clean_text(link.get_text(" ", strip=True))
        if len(text) >= 20:
            return text

    return ""


def extract_url(container):
    links = container.find_all("a", href=True)

    # First preference: a link whose visible text matches the story headline.
    headline = extract_headline(container)

    for link in links:
        href = link.get("href", "").strip()
        link_text = clean_text(link.get_text(" ", strip=True))

        if not href:
            continue

        if href.startswith("#") or href.startswith("javascript:"):
            continue

        absolute_url = urljoin(ENB_HOMEPAGE, href)

        if "energynewsbulletin.net" not in absolute_url:
            continue

        # Ignore category/navigation links.
        if "/category/" in absolute_url:
            continue

        if headline and link_text == headline:
            return absolute_url

    # Second preference: any non-category ENB article link.
    for link in links:
        href = link.get("href", "").strip()

        if not href:
            continue

        if href.startswith("#") or href.startswith("javascript:"):
            continue

        absolute_url = urljoin(ENB_HOMEPAGE, href)

        if "energynewsbulletin.net" not in absolute_url:
            continue

        if "/category/" in absolute_url:
            continue

        return absolute_url

    return ""


def extract_standfirst(container, headline, target_date):
    candidates = []

    for element in container.find_all(["p", "div", "span"]):
        text = clean_text(element.get_text(" ", strip=True))

        if not text:
            continue

        if text == headline:
            continue

        if target_date.lower() in text.lower():
            continue

        if len(text) < 25:
            continue

        if len(text) > 500:
            continue

        candidates.append(text)

    if candidates:
        return candidates[0]

    return ""


def find_today_stories(html, target_date):
    soup = BeautifulSoup(html, "html.parser")

    matching_text_nodes = soup.find_all(
        string=lambda text: (
            text
            and target_date.lower() in clean_text(text).lower()
        )
    )

    stories = []
    seen_urls = set()

    for text_node in matching_text_nodes:
        container = find_story_container(text_node)

        if not container:
            continue

        headline = extract_headline(container)
        url = extract_url(container)

        if not headline or not url:
            continue

        if url in seen_urls:
            continue

        seen_urls.add(url)

        standfirst = extract_standfirst(
            container,
            headline,
            target_date,
        )

        stories.append(
            {
                "headline": headline,
                "standfirst": standfirst,
                "url": url,
            }
        )

    return stories


def main():
    target_date = "17 August 2026"

    print()
    print(f"Looking for ENB stories dated: {target_date}")

    html = fetch_homepage()

    now = datetime.now(PERTH_TIMEZONE)

    date_variants = [
        now.strftime("%d %B %Y").lstrip("0"),
        now.strftime("%d %b %Y").lstrip("0"),
        now.strftime("%Y-%m-%d"),
        now.strftime("%d/%m/%Y"),
    ]

    print()
    print("DATE FORMAT DIAGNOSTIC")

    for variant in date_variants:
        count = html.lower().count(variant.lower())
        print(f"{variant}: {count} matches")

        if count:
            position = html.lower().find(variant.lower())
            start = max(0, position - 300)
            end = min(len(html), position + 500)

            print("Sample HTML:")
            print(html[start:end])
            print("-" * 70)

    stories = find_today_stories(
        html,
        target_date,
    )
        # Always place "News in brief" at the bottom.
    stories.sort(
        key=lambda story: story["headline"].strip().lower() == "news in brief"
    )
    
    print()
    print("=" * 70)
    print(f"ENERGY NEWS BULLETIN — {target_date}")
    print("=" * 70)

    if not stories:
        print()
        print("No matching ENB stories found.")
        return

    print()
    print(f"Stories found: {len(stories)}")
    print()

    for number, story in enumerate(stories, start=1):
        print(f"{number}. {story['headline']}")

        if story["standfirst"]:
            print(story["standfirst"])

        print(story["url"])
        print()


if __name__ == "__main__":
    main()
