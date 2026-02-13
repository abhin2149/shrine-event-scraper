import requests
import os
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from datetime import datetime
import pytz
import uuid
import platform
# --- 1. USER CONFIGURATION ---

BREVO_API_KEY = os.environ.get("BREVO_API_KEY")
SENDER_EMAIL = "vadhera.abhinav@gmail.com"
SENDER_NAME = "Exposition Park Event Bot"

RECEIVER_EMAIL = "psahagun@usc.edu"
RECEIVER_NAME = "Pablo Sahagun"

API_BASE = "https://expositionpark.ca.gov/wp-json/tribe/events/v1/events"


# --- 2. FETCH EVENTS FROM REST API ---
def format_datetime_nicely(dt_str):
    """
    Convert '2026-02-26 17:00:00' → '26th Feb, 5:00 pm'
    Works on Windows and Unix.
    """
    if not dt_str:
        return ""

    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return dt_str  # fallback if parsing fails

    day = dt.day
    # ordinal suffix
    if 4 <= day <= 20 or 24 <= day <= 30:
        suffix = "th"
    else:
        suffix = ["st", "nd", "rd"][day % 10 - 1]

    # cross-platform no-leading-zero day/hour
    day_fmt = "%#d" if platform.system() == "Windows" else "%-d"
    hour_fmt = "%#I" if platform.system() == "Windows" else "%-I"

    month = dt.strftime("%b").capitalize()

    formatted = dt.strftime(f"{day_fmt}{suffix} {month}, {hour_fmt}:%M %p")
    return formatted


def fetch_expo_events_via_api(start_date, end_date):
    """
    Fetch events via the Tribe REST API for the given date range.
    Uses a requests session with headers to avoid 403.
    Handles multiple venues per event.
    Only includes events where status == 'publish'.
    """
    session = requests.Session()

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://expositionpark.ca.gov/calendar/list/page/1/",
        "Connection": "keep-alive",
    }

    params = {
        "start_date": start_date,
        "end_date": end_date,
        "status": "publish",
        "per_page": 100
    }

    try:
        response = session.get(API_BASE, headers=headers, params=params, timeout=20)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return [], f"Error fetching API events: {e}"

    data = response.json()
    events_data = data.get("events") or data

    events = []

    for evt in events_data:
        if evt.get("status") != "publish":
            continue

        title = evt.get("title", "").strip()
        url = evt.get("url", "").strip()

        # Handle single or multiple venues
        venue_field = evt.get("venue")
        locations = []
        if isinstance(venue_field, dict):
            # Single venue
            name = venue_field.get("venue", "").strip()
            addr = venue_field.get("address", "").strip()
            locations.append(f"{name}, {addr}".strip(", "))
        elif isinstance(venue_field, list):
            # Multiple venues
            for v in venue_field:
                name = v.get("venue", "").strip()
                addr = v.get("address", "").strip()
                locations.append(f"{name}, {addr}".strip(", "))

        location_str = " | ".join(locations)

        start_dt = format_datetime_nicely(evt.get("start_date", ""))
        end_dt = format_datetime_nicely(evt.get("end_date", ""))

        events.append({
            "Name": title,
            "URL": url,
            "Venue": location_str,  # combined venues
            "Location": location_str,
            "Start_Date": start_dt,
            "End_Date": end_dt
        })

    if not events:
        return [], "No events found for that date range."

    return events, None


# --- 3. FORMAT EVENTS AS HTML ---

def format_api_events_as_html(event_list):
    pacific = pytz.timezone("US/Pacific")
    generated_at = datetime.now(pacific).strftime("%a %b %d · %I:%M %p %Z")
    event_count = len(event_list) if event_list else 0

    if not event_list:
        return "<h1>Exposition Park Event Report</h1><p>No events found.</p>"

    html = "<html><body>"
    html += f"<p><b>Generated:</b> {generated_at}<br>"
    html += f"<b>Total events:</b> {event_count}</p><hr>"

    html += """
    <table border="1" cellpadding="8"
           style="width:100%; border-collapse:collapse; font-family:Arial;">
        <thead>
            <tr style="background:#f2f2f2;">
                <th>Event</th>
                <th>Start Date</th>
                <th>End Date</th>
                <th>Location</th>
                <th>Link</th>
            </tr>
        </thead><tbody>
    """

    for event in event_list:
        html += f"""
        <tr>
            <td><b>{event['Name']}</b></td>
            <td>{event['Start_Date']}</td>
            <td>{event['End_Date']}</td>
            <td>{event['Location']}</td>
            <td><a href="{event['URL']}">View</a></td>
        </tr>
        """

    html += "</tbody></table></body></html>"
    return html

# --- 4. BREVO EMAIL SENDER ---

def send_email_with_brevo(html_content, subject):
    if not BREVO_API_KEY:
        print("BREVO_API_KEY not set. Email not sent.")
        return

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = BREVO_API_KEY

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
        sib_api_v3_sdk.ApiClient(configuration)
    )

    send_email = sib_api_v3_sdk.SendSmtpEmail(
        headers={
            "X-Report-Venue": "Exposition Park",
            "X-Report-Date": datetime.now().strftime("%Y-%m-%d"),
            "X-Report-Run-ID": str(uuid.uuid4())
        },
        to=[{"email": RECEIVER_EMAIL, "name": RECEIVER_NAME}],
        sender={"email": SENDER_EMAIL, "name": SENDER_NAME},
        subject=subject,
        html_content=html_content
    )

    try:
        api_instance.send_transac_email(send_email)
        print("Email sent successfully.")
    except ApiException as e:
        print(f"Email failed: {e}")

# --- 5. RUN SCRIPT ---

if __name__ == "__main__":
    # Fetch events for February 2026
    events, error = fetch_expo_events_via_api("2026-02-01", "2026-02-28")
    if error:
        print(error)
    else:
        html_report = format_api_events_as_html(events)
        # print(html_report)
        send_email_with_brevo(html_report, "Exposition Park February 2026 Events")
