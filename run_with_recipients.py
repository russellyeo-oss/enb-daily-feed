from datetime import datetime
from zoneinfo import ZoneInfo
import sys

PERTH_TIMEZONE = ZoneInfo("Australia/Perth")


def get_recipient():
    weekday = datetime.now(PERTH_TIMEZONE).weekday()
    recipients = ["russell.yeo@aspermont.com"]

    if weekday in (0, 2):
        recipients.append("katie.hobbins@aspermont.com")

    if weekday == 4:
        recipients.append("sofia.fimognari@aspermont.com")

    return ", ".join(recipients)


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in {"daily", "linkedin"}:
        raise SystemExit("Usage: python run_with_recipients.py [daily|linkedin]")

    if sys.argv[1] == "daily":
        import enb_daily_feed as module
    else:
        import enb_linkedin_feed as module

    module.get_recipient = get_recipient
    module.main()


if __name__ == "__main__":
    main()
