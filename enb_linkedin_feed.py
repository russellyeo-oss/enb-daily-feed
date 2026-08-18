from datetime import datetime
from zoneinfo import ZoneInfo
from openai import OpenAI

from enb_daily_feed import (
    fetch_homepage,
    find_today_stories,
    get_target_date,
    get_recipient,
    send_email,
)


PERTH_TIMEZONE = ZoneInfo("Australia/Perth")

client = OpenAI()

def build_linkedin_body(stories):
    story_text = []

    for story in stories:
        headline = story["headline"].strip()
        standfirst = story["standfirst"].strip()

        story_text.append(
            f"HEADLINE: {headline}\n"
            f"STANDFIRST: {standfirst}"
        )

    source_material = "\n\n".join(story_text)

    prompt = f"""
You are writing LinkedIn teases for Energy News Bulletin.

Using ONLY the supplied ENB headlines and standfirsts, rewrite each story
into a high-converting tease for a business audience.

Rules:
- Return one tease for each supplied story.
- Number them 1., 2., 3. and so on.
- No heading or introductory text.
- Each numbered item must end with a full stop.
- Write concise, punchy business-news teases.
- Preserve the factual meaning of the source material.
- Do not invent facts, figures, quotes or context.
- Use hashtags sparingly.
- Only hashtag genuine, useful industry or topic terms.
- Multi-word hashtags must use CamelCase, for example #RenewableEnergy.
- Do not invent awkward hashtags from ordinary phrases.
- Do not add links, subscription text or a footer.
- Keep "News in brief" as the final item if it is present.

SOURCE MATERIAL:

{source_material}
"""

    response = client.responses.create(
        model="gpt-5-mini",
        input=prompt,
    )

    linkedin_text = response.output_text.strip()

    return (
        "Do you subscribe to our newsletter?\n"
        "If not, here’s what you’re missing out on…\n\n"
        f"{linkedin_text}\n\n\n"
        "All that and more.\n"
        "https://lnkd.in/etZanhq\n\n"
        "https://subscriptions.energynewsbulletin.net/subscribe?sourcecode=ENBDigitalMonthlyFreeFirstMonth"
    )
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
