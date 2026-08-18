from datetime import datetime
from zoneinfo import ZoneInfo

from enb_daily_feed import (
    fetch_homepage,
    find_today_stories,
    get_target_date,
    get_recipient,
    send_email,
)


PERTH_TIMEZONE = ZoneInfo("Australia/Perth")


def build_linkedin_body(stories):
    lines = []

    for story in stories:
        headline = story["headline"].strip()
        standfirst = story["standfirst"].strip()

        if standfirst:
            line = f"{headline} - {standfirst}"
        else:
            line = headline

        if not line.endswith("."):
            line += "."

        lines.append(f"• {line}")

    return "\n".join(lines)


def main():
    target_date = get_target_date()
    recipient = get_recipient()

    print(f"Looking for ENB stories dated: {target_date}")
    print(f"Recipient for today: {recipient}")

    html = fetch_homepage()

    stories = find_today_stories(
        html,
        target_date,
    )

    stories.sort(
        key=lambda story: story["headline"].strip().lower() == "news in brief"
    )

    if not stories:
        print("No matching ENB stories found.")
        return

    print(f"Stories found: {len(stories)}")

    body = build_linkedin_body(stories)
    subject = datetime.now(PERTH_TIMEZONE).strftime("%A")

    send_email(
        recipient,
        subject,
        body,
    )

    print()
    print("LINKEDIN EMAIL PREVIEW")
    print("=" * 70)
    print(body)
    print("=" * 70)


if __name__ == "__main__":
    main()
