import requests
from bs4 import BeautifulSoup
import os
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

# --- 1. USER CONFIGURATION for Brevo Email ---

BREVO_API_KEY = os.environ.get("BREVO_API_KEY")
SENDER_EMAIL = "vadhera.abhinav@gmail.com"  # UPDATE IF NEEDED
SENDER_NAME = "BMO Stadium Event Bot"

RECEIVER_EMAIL = "psahagun@usc.edu"  # CONFIRM
RECEIVER_NAME = "Pablo Sahagun"

MAIN_URL = "https://bmostadium.com/upcoming-events/"

# --- 2. CORE SCRAPING LOGIC ---

def extract_bmo_events(main_url):
    """
    Fetches the BMO Stadium upcoming events page, extracts event links,
    then scrapes each event page for title, date, time, and location.
    """
    print(f"--- Fetching BMO Stadium events from: {main_url} ---")

    try:
        response = requests.get(main_url, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return None, f"Error fetching main page: {e}"

    soup = BeautifulSoup(response.content, "html.parser")
    events = []

    event_cards = soup.select(".grid.col-4.event-grid .grid__item.card")

    if not event_cards:
        return [], "No event cards found. Selector may be outdated."

    print(f"Found {len(event_cards)} event links. Processing...\n")

    for card in event_cards:
        link = card.select_one(".card__image a")
        if not link:
            continue

        event_url = link.get("href")
        print(f"-> Scraping event page: {event_url}")

        try:
            event_response = requests.get(event_url, timeout=15)
            event_response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"   Failed to fetch {event_url}: {e}")
            continue

        event_soup = BeautifulSoup(event_response.content, "html.parser")

        # --- Extract fields from event page ---
        title_tag = event_soup.select_one(".header h2")
        date_tag = event_soup.select_one(".event__date p")
        time_tag = event_soup.select_one(".event__time p")

        title = title_tag.get_text(strip=True) if title_tag else "N/A"
        date = date_tag.get_text(strip=True) if date_tag else "N/A"
        time = time_tag.get_text(strip=True) if time_tag else "N/A"

        # Location inference
        location = "BMO Stadium"
        if "Coliseum" in title:
            location = "LA Coliseum"

        events.append({
            "Name": title,
            "Date": date,
            "Time": time,
            "Location": location,
            "URL": event_url
        })

        print(f"   Name: {title}")
        print(f"   Date: {date}")
        print(f"   Time: {time}")
        print(f"   Location: {location}")
        print("-" * 50)

    return events, None

# --- 3. FORMAT EVENTS AS HTML ---

from datetime import datetime
import pytz
import uuid

def format_events_as_html(event_list):
    # --- Entropy block ---
    pacific = pytz.timezone("US/Pacific")
    generated_at = datetime.now(pacific).strftime("%a %b %d · %I:%M %p %Z")
    event_count = len(event_list) if event_list else 0

    if not event_list:
        return "<h1>BMO Stadium Event Report</h1><p>No upcoming events found.</p>"

    html = "<html><body>"
    html += f"<p><b>Generated at:</b> {generated_at}<br><b>Source:</b> BMO Stadium<br><b>Events detected:</b> {event_count}</p><hr>"
    html += "<h1>🏟️ BMO Stadium Upcoming Events</h1>"
    html += f"<p>Found {len(event_list)} upcoming events</p>"

    html += """
    <table border="1" cellpadding="10" cellspacing="0" style="width:100%; border-collapse:collapse; font-family:Arial, sans-serif;">
        <thead>
            <tr style="background-color:#f2f2f2;">
                <th>Event Name</th>
                <th>Date</th>
                <th>Time</th>
                <th>Location</th>
                <th>Event Link</th>
            </tr>
        </thead>
        <tbody>
    """

    for event in event_list:
        time_style = "color:#ff8c00; font-weight:bold;" if event['Time'] in ("N/A", "TBD") else ""
        html += f"""
        <tr>
            <td><b>{event['Name']}</b></td>
            <td>{event['Date']}</td>
            <td style="{time_style}">{event['Time']}</td>
            <td>{event['Location']}</td>
            <td><a href="{event['URL']}" target="_blank">View Event</a></td>
        </tr>
        """

    html += "</tbody></table></body></html>"
    return html

# --- 4. SEND EMAIL VIA BREVO ---

def send_email_with_brevo(html_content, subject):
    run_id = str(uuid.uuid4())
    report_date = datetime.now().strftime("%Y-%m-%d")
    if not BREVO_API_KEY:
        print("BREVO_API_KEY not set. Email not sent.")
        return

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = BREVO_API_KEY

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
        sib_api_v3_sdk.ApiClient(configuration)
    )

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        headers={
            "X-Report-Venue": "BMO Stadium",
            "X-Report-Date": report_date,
            "X-Report-Run-ID": run_id
        },

        to=[{"email": RECEIVER_EMAIL, "name": RECEIVER_NAME}],
        sender={"email": SENDER_EMAIL, "name": SENDER_NAME},
        subject=subject,
        html_content=html_content
    )

    try:
        response = api_instance.send_transac_email(send_smtp_email)
        print("Email sent successfully.")
        print(f"Message ID: {response.message_id}")
    except ApiException as e:
        print(f"Failed to send email: {e}")

# --- 5. RUN SCRIPT ---

if __name__ == "__main__":
    events, error = extract_bmo_events(MAIN_URL)

    if error:
        error_html = f"<h1>🚨 BMO Scraping Error</h1><p>{error}</p>"
        # send_email_with_brevo(error_html, "ACTION REQUIRED: BMO Scraper Error")
    else:
        html_report = format_events_as_html(events)
        send_email_with_brevo(html_report, "BMO Stadium Event Report")
