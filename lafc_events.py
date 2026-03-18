import requests
import os
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

from datetime import datetime
import pytz
import uuid

BREVO_API_KEY = os.environ.get("BREVO_API_KEY")

SENDER_EMAIL = "info@abhinavvadhera.me"
SENDER_NAME = "LAFC Game Bot"

RECEIVER_EMAIL = "psahagun@usc.edu"
RECEIVER_NAME = "Pablo Sahagun"

ICS_URL = "https://raw.githubusercontent.com/jbaranski/majorleaguesoccer-ical/refs/heads/main/calendars/losangelesfc.ics"


def extract_lafc_games(url):

    print(f"Fetching LAFC schedule...")

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return None, str(e)

    lines = response.text.splitlines()

    games = []
    current = {}

    for line in lines:

        if line.startswith("BEGIN:VEVENT"):
            current = {}

        elif line.startswith("SUMMARY:"):
            current["Name"] = line.replace("SUMMARY:", "")

        elif line.startswith("DTSTART"):
            current["RawDate"] = line.split(":")[1]

        elif line.startswith("LOCATION:"):

            raw_location = line.replace("LOCATION:", "")

            # Remove anything after "/"
            clean_location = raw_location.split("/")[0].strip()
            if "BMO Stadium" in clean_location:
                clean_location = "BMO Stadium"

            elif "Coliseum" in clean_location:
                clean_location = "Los Angeles Memorial Coliseum"

            current["Location"] = clean_location

        elif line.startswith("END:VEVENT"):

            location = current.get("Location", "")

            if "BMO Stadium" in location or "Coliseum" in location:

                utc = pytz.utc
                pacific = pytz.timezone("US/Pacific")

                raw = current.get("RawDate")

                dt = datetime.strptime(raw, "%Y%m%dT%H%M%SZ")
                dt = utc.localize(dt)
                dt = dt.astimezone(pacific)

                formatted_date = dt.strftime("%b %d, %Y")
                formatted_time = dt.strftime("%I:%M %p PT")

                games.append({
                    "Name": current.get("Name", "N/A"),
                    "Date": formatted_date,
                    "Time": formatted_time,
                    "Location": location,
                    "URL": "https://www.lafc.com/schedule"
                })

    print(f"Found {len(games)} LAFC games.")

    return games, None


def format_events_as_html(event_list):

    pacific = pytz.timezone("US/Pacific")
    generated_at = datetime.now(pacific).strftime("%a %b %d · %I:%M %p %Z")

    html = "<html><body>"

    html += f"<p><b>Generated:</b> {generated_at}<br>"
    html += f"<b>Total games:</b> {len(event_list)}</p><hr>"

    html += "<h1>⚽ LAFC Games</h1>"

    # --- GROUP EVENTS BY MONTH ---
    grouped = {}

    for event in event_list:

        dt = datetime.strptime(event["Date"], "%b %d, %Y")
        month_key = dt.strftime("%B %Y")

        if month_key not in grouped:
            grouped[month_key] = []

        grouped[month_key].append(event)

    # --- BUILD HTML ---
    for month in grouped:

        html += f"<h2>{month}</h2>"

        html += """
        <table border="1" cellpadding="10" cellspacing="0"
        style="width:100%; border-collapse:collapse; font-family:Arial; margin-bottom:25px;">
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

        for event in grouped[month]:

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

    pacific = pytz.timezone("US/Pacific")
    generated_at = datetime.now(pacific).strftime("%a %b %d · %I:%M %p %Z")

    html = "<html><body>"

    html += f"<p><b>Generated:</b> {generated_at}<br>"
    html += f"<b>Total games:</b> {len(event_list)}</p><hr>"

    html += "<h1>LAFC Games</h1>"

    html += """
    <table border="1" cellpadding="10" cellspacing="0"
    style="width:100%; border-collapse:collapse; font-family:Arial;">
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

    for event in event_list:

        html += f"""
        <tr>
        <td><b>{event['Name']}</b></td>
        <td>{event['Date']}</td>
        <td>{event['Time']}</td>
        <td>{event['Location']}</td>
        <td><a href="{event['URL']}">View Schedule</a></td>
        </tr>
        """

    html += "</tbody></table></body></html>"

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

    events, error = extract_lafc_games(ICS_URL)

    if error:
        print(error)
    else:
        html = format_events_as_html(events)
        # print(html)
        send_email_with_brevo(html, "LAFC Games")
