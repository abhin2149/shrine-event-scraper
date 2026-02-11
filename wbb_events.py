import requests
import os
from bs4 import BeautifulSoup
from datetime import datetime
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

MAIN_URL = "https://usctrojans.com/sports/womens-basketball/schedule/text"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; USC-Basketball-Scraper/1.0)"
}

# -------------------------------------------------
# 2. CORE SCRAPING LOGIC (TEXT TABLE)
# -------------------------------------------------

def extract_usc_womens_basketball_games(url):
    """
    Scrapes USC Women's Basketball schedule from the TEXT view table.
    Adds academic year dynamically.
    """

    print(f"--- Fetching USC Women's Basketball Schedule from: {url} ---")

    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return None, f"Error fetching schedule page: {e}"

    soup = BeautifulSoup(response.text, "html.parser")

    table = soup.find("table")
    if not table:
        return [], "Schedule table not found. Page structure may have changed."

    rows = table.find("tbody").find_all("tr")
    games = []

    # Determine academic year
    today = datetime.today()
    if today.month >= 8:
        season_start_year = today.year
    else:
        season_start_year = today.year - 1

    for row in rows:
        cols = [c.get_text(strip=True) for c in row.find_all("td")]

        if len(cols) < 7:
            continue

        date_raw = cols[0]
        time = cols[1]
        at_flag = cols[2]
        opponent = cols[3]
        location = cols[4]
        tournament = cols[5]
        result = cols[6]

        # Build title
        at_vs = "at" if at_flag.lower() == "at" else "vs"
        title = f"USC {at_vs} {opponent}"

        # Add academic year to date
        date_str = "TBD"
        if date_raw and date_raw != "TBD":
            try:
                month_abbr = date_raw.split()[0]
                month_num = datetime.strptime(month_abbr, "%b").month
                year = season_start_year if month_num >= 8 else season_start_year + 1
                date_str = f"{date_raw} {year}"
            except Exception:
                date_str = date_raw

        games.append({
            "title": title,
            "location": {
                "venue": location,
                "city_state": ""
            },
            "date": date_str,
            "time": time,
            "result": result
        })

    return games, None

# -------------------------------------------------
# 3. EMAIL BODY BUILDER
# -------------------------------------------------

def format_basketball_games_as_html(games):
    if not games:
        return "<h1>🏀 USC Women’s Basketball</h1><p>No games found.</p>"

    html = "<html><body>"
    html += "<h1>🏀 USC Women’s Basketball Schedule & Results</h1>"
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

        html += f"""
        <tr>
            <td><b>{game["title"]}</b></td>
            <td>{game["date"]}</td>
            <td>{game["time"]}</td>
            <td>{game["location"]["venue"]}</td>
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
        print("✅ USC Women’s Basketball email sent successfully.")
    except ApiException as e:
        print(f"❌ Failed to send email via Brevo: {e}")

# -------------------------------------------------
# 5. RUN SCRIPT
# -------------------------------------------------

if __name__ == "__main__":

    games, error = extract_usc_womens_basketball_games(MAIN_URL)

    if error:
        error_html = f"""
        <h1>🚨 USC Women’s Basketball Scraper Error</h1>
        <p>{error}</p>
        """
        send_email_with_brevo(
            error_html,
            "ACTION REQUIRED: USC Women’s Basketball Scraper Error"
        )
    else:
        email_body = format_basketball_games_as_html(games)
        print(email_body)
        send_email_with_brevo(
            email_body,
            "🏀 USC Women’s Basketball Schedule & Results"
        )
