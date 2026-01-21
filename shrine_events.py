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

SENDER_EMAIL = "vadhera.abhinav@gmail.com"
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
    """Formats events into HTML for the email."""
    print("Formatting events into HTML...")

    now_utc = datetime.now(pytz.utc)
    now_pt = now_utc.astimezone(pytz.timezone("America/Los_Angeles"))
    formatted_now = now_pt.strftime("%a %b %d · %I:%M %p PT")

    entropy_html = f"""
    <p><b>Generated at:</b> {formatted_now}<br>
       <b>Source:</b> Shrine Auditorium<br>
       <b>Events detected:</b> {len(event_list)}</p>
    <hr>
    """

    html_body = "<html><body>"
    html_body += "<h1>Shrine Auditorium Event Update</h1>"
    html_body += entropy_html

    for event in event_list:
        try:
            event_name = event['title']['headlinersText']
            date_str = event['eventDateTime']
            is_active = event['ticketing']['statusId'] == 1

            dt = parser.parse(date_str)
            formatted_date = dt.strftime("%A, %B %d, %Y")
            formatted_time = dt.strftime("%I:%M %p")

            event_status = "Active" if is_active else "Cancelled/Inactive"
            status_color = "green" if is_active else "red"

            html_body += f"""
            <div style="margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid #eee;">
                <h3 style="margin-bottom: 5px;">{event_name}</h3>
                <p style="margin: 0; font-size: 1.1em;">
                    {formatted_date} at {formatted_time}
                </p>
                <p style="margin: 5px 0 0 0;">
                    Status: <b style="color: {status_color};">{event_status}</b>
                </p>
            </div>
            """
        except KeyError as e:
            print(f"Warning: Skipping an event due to missing key: {e}")

    html_body += "</body></html>"
    return html_body

def send_email_with_brevo(html_content):
    """Connects to Brevo and sends the email with custom headers containing micro-entropy."""
    if not BREVO_API_KEY:
        print("---\nERROR: BREVO_API_KEY not found.\n---")
        return

    print(f"Connecting to Brevo and sending email to {RECEIVER_EMAIL}...")

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = BREVO_API_KEY
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    
    subject = "Shrine Auditorium Event Report"
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
