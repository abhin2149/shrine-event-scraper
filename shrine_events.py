import requests
import json
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from dateutil import parser
import os
from datetime import datetime
import pytz
import uuid  # For unique run ID

# --- 1. USER CONFIGURATION ---

BREVO_API_KEY = os.environ.get("BREVO_API_KEY")

SENDER_EMAIL = "info@abhinavvadhera.me"
SENDER_NAME = "Shrine Event Bot"

RECEIVER_EMAIL = "psahagun@usc.edu"
RECEIVER_NAME = "Pablo Sahagun"

API_URL = "https://aegwebprod.blob.core.windows.net/json/events/45/events.json"

# --- 2. SCRIPT LOGIC (Fetching and Parsing) ---

def fetch_events():
    """Fetches the raw event list from the API."""
    print(f"Fetching event data from {API_URL}...")
    try:
        response = requests.get(API_URL)
        response.raise_for_status()
        data = response.json()
        return data['events']
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to fetch data from the URL. {e}")
    except json.JSONDecodeError:
        print("ERROR: Failed to parse the response as JSON.")
    except KeyError:
        print("ERROR: The key 'events' was not found in the JSON.")
    return None


def format_events_as_html(event_list):
    """Formats events into HTML table (aligned with USC volleyball email style)."""

    if not event_list:
        return "<h1>🎭 Shrine Auditorium Events</h1><p>No events found.</p>"

    now_utc = datetime.now(pytz.utc)
    now_pt = now_utc.astimezone(pytz.timezone("America/Los_Angeles"))
    formatted_now = now_pt.strftime("%a %b %d · %I:%M %p PT")

    html = "<html><body>"
    html += "<h1>🎭 Shrine Auditorium Event Report</h1>"

    html += f"""
    <p>
        <b>Generated at:</b> {formatted_now}<br>
        <b>Source:</b> Shrine Auditorium<br>
        <b>Events found:</b> {len(event_list)}
    </p>
    """

    html += """
    <table border="1" cellpadding="10" cellspacing="0"
           style="width:100%; border-collapse:collapse; font-family:Arial,sans-serif;">
        <thead>
            <tr style="background-color:#f2f2f2;">
                <th align="left">Event</th>
                <th align="left">Date</th>
                <th align="left">Time</th>
                <th align="left">Status</th>
            </tr>
        </thead>
        <tbody>
    """

    for event in event_list:
        try:
            event_name = event['title']['headlinersText']
            date_str = event['eventDateTime']
            is_active = event['ticketing']['statusId'] != 0

            dt = parser.parse(date_str)
            formatted_date = dt.strftime("%A, %B %d, %Y")
            formatted_time = dt.strftime("%I:%M %p")

            if is_active:
                status_text = "Active"
                status_style = "font-weight:bold; color:#1a7f37;"
            else:
                status_text = "Cancelled/Inactive"
                status_style = "font-weight:bold; color:#b42318;"

            html += f"""
            <tr>
                <td><b>{event_name}</b></td>
                <td>{formatted_date}</td>
                <td>{formatted_time}</td>
                <td style="{status_style}">{status_text}</td>
            </tr>
            """

        except KeyError as e:
            print(f"Warning: Skipping event due to missing key: {e}")

    html += "</tbody></table></body></html>"
    return html
    

def send_email_with_brevo(html_content):
    """Connects to Brevo and sends the email with custom headers containing micro-entropy."""
    if not BREVO_API_KEY:
        print("---\nERROR: BREVO_API_KEY not found.\n---")
        return

    print(f"Connecting to Brevo and sending email to {RECEIVER_EMAIL}...")

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = BREVO_API_KEY
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    
    subject = "🎭 Shrine Auditorium Event Report"
    sender = {"name": SENDER_NAME, "email": SENDER_EMAIL}
    to = [{"email": RECEIVER_EMAIL, "name": RECEIVER_NAME}]

    # --- MICRO-ENTROPY: UUID for unique run ID ---
    run_id = str(uuid.uuid4())

    headers = {
        "X-Report-Venue": "Shrine",
        "X-Report-Date": (datetime.now(pytz.timezone("America/Los_Angeles"))
                          .strftime("%Y-%m-%d")),
        "X-Report-Run-ID": run_id
    }

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=to,
        sender=sender,
        subject=subject,
        html_content=html_content,
        headers=headers
    )

    try:
        api_response = api_instance.send_transac_email(send_smtp_email)
        print("\n---")
        print("Success! Email sent via Brevo.")
        print(f"Message ID: {api_response.message_id}")
        print(f"Run ID: {run_id}")
        print("---")
    except ApiException as e:
        print(f"ERROR: Failed to send email via Brevo: {e}")

# --- 3. RUN THE SCRIPT ---

if __name__ == "__main__":
    raw_events = fetch_events()
    
    if raw_events:
        email_body = format_events_as_html(raw_events)
        send_email_with_brevo(email_body)
    else:
        print("No events found or error occurred, no email sent.")
