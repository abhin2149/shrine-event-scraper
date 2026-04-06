import requests
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

from datetime import datetime
import pytz
import uuid
import re
import json

BREVO_API_KEY = os.environ.get("BREVO_API_KEY")

SENDER_EMAIL = "info@abhinavvadhera.me"
SENDER_NAME = "Angel City Game Bot"

RECEIVER_EMAIL = "psahagun@usc.edu"
RECEIVER_NAME = "Pablo Sahagun"

SCHEDULE_URL = "https://angelcity.com/2026-schedule"


def extract_angel_city_games(url):
    print("Fetching Angel City schedule...")

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return None, str(e)

    html = response.text

    # --- Extract gamesData ---
    match = re.search(r"const gamesData = \[(.*?)\];", html, re.DOTALL)

    if not match:
        return None, "gamesData not found"

    games_raw = "[" + match.group(1) + "]"

    # ✅ Quote ONLY keys that appear after { or ,
    games_json = re.sub(r'([{,]\s*)(\w+):', r'\1"\2":', games_raw)

    # Replace single quotes with double quotes
    games_json = games_json.replace("'", '"')

    # Remove trailing commas
    games_json = re.sub(r',\s*}', '}', games_json)
    games_json = re.sub(r',\s*]', ']', games_json)

    try:
        games_data = json.loads(games_json)
    except Exception as e:
        print("DEBUG JSON SAMPLE:\n", games_json[:1000])
        return None, f"JSON parse error: {e}"
    

    games = []

    utc = pytz.utc
    pacific = pytz.timezone("US/Pacific")

    for game in games_data:

        raw_date = game.get("date")
        opponent = game.get("opponent")
        game_type = game.get("gameType")

        dt = datetime.strptime(raw_date, "%Y-%m-%d %H:%M:%S")
        dt = utc.localize(dt)
        dt = dt.astimezone(pacific)

        formatted_date = dt.strftime("%b %d, %Y")
        formatted_time = dt.strftime("%I:%M %p PT")

        if game_type == "home":
            games.append({
            "Name": f"vs {opponent}" if game_type == "home" else f"@ {opponent}",
            "Date": formatted_date,
            "Time": formatted_time,
            "Location": "BMO Stadium",
            "URL": url
        })

    print(f"Found {len(games)} Angel City games.")

    return games, None


def format_events_as_html(event_list):
    pacific = pytz.timezone("US/Pacific")
    generated_at = datetime.now(pacific).strftime("%a %b %d · %I:%M %p %Z")

    html = "<html><body>"

    html += f"<p><b>Generated:</b> {generated_at}<br>"
    html += f"<b>Total games:</b> {len(event_list)}</p><hr>"

    html += "<h1>⚽ Angel City FC Games</h1>"

    # Group by month
    grouped = {}

    for event in event_list:
        dt = datetime.strptime(event["Date"], "%b %d, %Y")
        month_key = dt.strftime("%B %Y")

        if month_key not in grouped:
            grouped[month_key] = []

        grouped[month_key].append(event)

    # Consistent table template
    table_header = """
    <table border="1"
           cellpadding="10"
           cellspacing="0"
           style="width:100%;
                  border-collapse:collapse;
                  font-family:Arial;
                  margin-bottom:25px;
                  table-layout:fixed;">
        <colgroup>
            <col style="width:25%;">
            <col style="width:15%;">
            <col style="width:15%;">
            <col style="width:25%;">
            <col style="width:20%;">
        </colgroup>
        <thead>
            <tr style="background-color:#f2f2f2;">
                <th>Match</th>
                <th>Date</th>
                <th>Time</th>
                <th>Location</th>
                <th>Schedule</th>
            </tr>
        </thead>
        <tbody>
    """

    # Sort months chronologically
    sorted_months = sorted(
        grouped.keys(),
        key=lambda x: datetime.strptime(x, "%B %Y")
    )

    for month in sorted_months:
        html += f"<h2>{month}</h2>"
        html += table_header

        # Sort games within month by date
        sorted_events = sorted(
            grouped[month],
            key=lambda e: datetime.strptime(e["Date"], "%b %d, %Y")
        )

        for event in sorted_events:
            html += f"""
            <tr>
                <td><b>{event['Name']}</b></td>
                <td>{event['Date']}</td>
                <td>{event['Time']}</td>
                <td>{event['Location']}</td>
                <td><a href="{event['URL']}">View Schedule</a></td>
            </tr>
            """

        html += "</tbody></table>"

    html += "</body></html>"

    return html


def send_email_with_brevo(html_content, subject):

    run_id = str(uuid.uuid4())

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = BREVO_API_KEY

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
        sib_api_v3_sdk.ApiClient(configuration)
    )

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": RECEIVER_EMAIL, "name": RECEIVER_NAME}],
        sender={"email": SENDER_EMAIL, "name": SENDER_NAME},
        subject=subject,
        html_content=html_content,
        headers={"X-Run-ID": run_id}
    )

    try:
        api_instance.send_transac_email(send_smtp_email)
        print("Email sent successfully")

    except ApiException as e:
        print("Email failed:", e)


if __name__ == "__main__":

    events, error = extract_angel_city_games(SCHEDULE_URL)

    if error:
        print(error)
    else:
        html = format_events_as_html(events)
        # print(html)
        send_email_with_brevo(html, "Angel City FC Schedule")
