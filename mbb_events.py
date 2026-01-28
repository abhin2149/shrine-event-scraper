import requests
import json
from bs4 import BeautifulSoup
import os
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

# -------------------------------------------------
# 1. USER CONFIGURATION (Brevo Email)
# -------------------------------------------------

BREVO_API_KEY = os.environ.get("BREVO_API_KEY")

SENDER_EMAIL = "vadhera.abhinav@gmail.com"
SENDER_NAME = "USC Basketball Bot"

RECEIVER_EMAIL = "psahagun@usc.edu"
RECEIVER_NAME = "Pablo Sahagun"

MAIN_URL = "https://usctrojans.com/sports/mens-basketball/schedule"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; USC-Basketball-Scraper/1.0)"
}

# -------------------------------------------------
# 2. CORE SCRAPING LOGIC
# -------------------------------------------------

from datetime import datetime
import requests
from bs4 import BeautifulSoup

def extract_usc_basketball_games(url):
    """
    Scrapes USC Men's Basketball schedule using HTML parsing.
    Automatically determines the academic year and adds the correct year to each date.
    Works for all past and future games.
    """
    print(f"--- Fetching USC Basketball Schedule from: {url} ---")

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (compatible; USC-Basketball-Scraper/1.0)"
    }

    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return None, f"Error fetching schedule page: {e}"

    soup = BeautifulSoup(response.text, "html.parser")
    games = []

    # Determine academic year dynamically
    today = datetime.today()
    if today.month >= 8:  # Aug–Dec
        season_start_year = today.year
    else:  # Jan–Jul
        season_start_year = today.year - 1

    game_cards = soup.select('[data-test-id="s-game-card-standard__root"]')
    if not game_cards:
        return [], "No game cards found. Selector may have changed."

    for card in game_cards:
        # -----------------------------
        # Opponent and vs/at
        # -----------------------------
        opponent_tag = card.select_one(
            '[data-test-id="s-game-card-standard__header-team-opponent-link"]'
        )
        opponent = opponent_tag.get_text(strip=True) if opponent_tag else "Unknown"

        at_vs_tag = card.select_one('[data-test-id="s-stamp__root"] span')
        at_vs = at_vs_tag.get_text(strip=True) if at_vs_tag else "vs"

        title = f"USC {at_vs} {opponent}"

        # -----------------------------
        # Location
        # -----------------------------
        venue_tag = card.select_one(
            '[data-test-id="s-game-card-facility-and-location__standard-facility-title"], \
             [data-test-id="s-game-card-facility-and-location__game-facility-title-link"]'
        )
        city_tag = card.select_one(
            '[data-test-id="s-game-card-facility-and-location__standard-location-details"]'
        )
        venue = venue_tag.get_text(strip=True) if venue_tag else ""
        city_state = city_tag.get_text(strip=True) if city_tag else ""

        # -----------------------------
        # Date (handle both past and future formats)
        # -----------------------------
        date_str = ""
        # 1. Past / early-season format
        date_container = card.select_one('[data-test-id="s-game-card-standard__header-game-date-details"]')
        if date_container:
            spans = date_container.find_all("span")
            if spans:
                date_str = " ".join(span.get_text(strip=True) for span in spans)
            else:
                date_str = date_container.get_text(strip=True)

        # 2. Future / later-season format
        if not date_str:
            date_tag = card.select_one('[data-test-id="s-game-card-standard__header-game-date"]')
            if date_tag:
                main_text = date_tag.contents[0].strip() if date_tag.contents else ""
                span_text = date_tag.find("span").get_text(strip=True) if date_tag.find("span") else ""
                date_str = f"{main_text} {span_text}".strip()

        # 3. Add year dynamically
        if date_str and date_str != "TBD":
            try:
                month_abbr = date_str.split()[0]  # e.g., "Mar"
                month_num = datetime.strptime(month_abbr, "%b").month
                year = season_start_year if month_num >= 8 else season_start_year + 1
                date_str = f"{date_str} {year}"
            except Exception:
                # fallback if month parsing fails
                pass
        else:
            date_str = "TBD"

        # -----------------------------
        # Time
        # -----------------------------
        time_tag = card.select_one('[aria-label="Event Time"]')
        time = time_tag.get_text(strip=True) if time_tag else ""

        # -----------------------------
        # Result
        # -----------------------------
        result_tag = card.select_one('[data-test-id="s-game-card-standard__header-game-team-score"]')
        result = result_tag.get_text(strip=True) if result_tag else ""

        # -----------------------------
        # Add to JSON
        # -----------------------------
        games.append({
            "title": title,
            "location": {"venue": venue, "city_state": city_state},
            "date": date_str,
            "time": time,
            "result": result
        })

    return games, None


# -------------------------------------------------
# 3. EMAIL BODY BUILDER (FROM JSON STRUCTURE)
# -------------------------------------------------

def format_basketball_games_as_html(games):
    """
    Builds the HTML email body directly from the basketball JSON structure.
    Adds year and visually distinguishes past vs upcoming games.
    """
    if not games:
        return "<h1>🏀 USC Men’s Basketball</h1><p>No games found.</p>"

    html = "<html><body>"
    html += "<h1>🏀 USC Men’s Basketball Schedule & Results</h1>"
    html += f"<p>Found {len(games)} games</p>"

    html += """
    <table border="1" cellpadding="10" cellspacing="0"
           style="width:100%; border-collapse:collapse; font-family:Arial,sans-serif;">
        <thead>
            <tr style="background-color:#f2f2f2;">
                <th align="left">Game</th>
                <th align="left">Date</th>
                <th align="left">Time</th>
                <th align="left">Location</th>
                <th align="left">Result</th>
            </tr>
        </thead>
        <tbody>
    """

    for game in games:
        result = game["result"]
        if result.startswith("W"):
            result_style = "font-weight:bold; color:#1a7f37;"
        elif result.startswith("L"):
            result_style = "font-weight:bold; color:#b42318;"
        else:
            result_style = "color:#666;"
        game_style = ""

        html += f"""
        <tr style="{game_style}">
            <td><b>{game["title"]}</b></td>
            <td>{game["date"]}</td>
            <td>{game["time"]}</td>
            <td>
                {game["location"]["venue"]}<br/>
                <span style="color:#666;">{game["location"]["city_state"]}</span>
            </td>
            <td style="{result_style}">{result}</td>
        </tr>
        """

    html += "</tbody></table></body></html>"
    return html



# -------------------------------------------------
# 4. EMAIL SENDING (Brevo)
# -------------------------------------------------

def send_email_with_brevo(html_content, subject):

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key["api-key"] = BREVO_API_KEY

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
        sib_api_v3_sdk.ApiClient(configuration)
    )

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": RECEIVER_EMAIL, "name": RECEIVER_NAME}],
        sender={"email": SENDER_EMAIL, "name": SENDER_NAME},
        subject=subject,
        html_content=html_content
    )

    try:
        api_instance.send_transac_email(send_smtp_email)
        print("✅ USC Basketball email sent successfully.")
    except ApiException as e:
        print(f"❌ Failed to send email via Brevo: {e}")


# -------------------------------------------------
# 5. RUN SCRIPT
# -------------------------------------------------

if __name__ == "__main__":

    games, error = extract_usc_basketball_games(MAIN_URL)

    if error:
        error_html = f"""
        <h1>🚨 USC Basketball Scraper Error</h1>
        <p>{error}</p>
        """
        send_email_with_brevo(
            error_html,
            "ACTION REQUIRED: USC Basketball Scraper Error"
        )
    else:
        email_body = format_basketball_games_as_html(games)
        send_email_with_brevo(
            email_body,
            "🏀 USC Men’s Basketball Schedule & Results"
        )
