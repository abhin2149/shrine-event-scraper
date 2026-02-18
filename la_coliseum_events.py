import requests
from bs4 import BeautifulSoup
import os 
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

# --- 1. USER CONFIGURATION for Brevo Email ---

# The API key will be read from the environment (e.g., GitHub Secrets)
BREVO_API_KEY = os.environ.get("BREVO_API_KEY")
# Replace with your VERIFIED Brevo sender email
SENDER_EMAIL = "vadhera.abhinav@gmail.com" # <-- **UPDATE THIS**
SENDER_NAME = "LA Coliseum Event Bot"

# The email address to send the report to
RECEIVER_EMAIL = "psahagun@usc.edu" # <-- **CONFIRM THIS**
RECEIVER_NAME = "Pablo Sahagun"

# The main URL to scrape
MAIN_URL = "https://www.lacoliseum.com/events/"

# --- 2. CORE SCRAPING LOGIC (Modified) ---

def extract_coliseum_events(main_url):
    """
    Fetches the LA Coliseum events page, extracts individual event links,
    and then fetches and extracts Name, Full Date, and Start Time for each event.
    """
    print(f"--- Fetching main event archive from: {main_url} ---")

    try:
        main_response = requests.get(main_url)
        main_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the main page: {e}")
        return None, f"Error fetching main page: {e}"

    main_soup = BeautifulSoup(main_response.content, 'html.parser')
    event_details = []
    
    event_boxes = main_soup.select('#archives .event-box')

    if not event_boxes:
        error_msg = "Could not find any event boxes. Check selector."
        print(error_msg)
        return [], error_msg

    print(f"Found {len(event_boxes)} event links. Fetching details for each...")
    print("-" * 50)
    
    # Process each event link
    for box in event_boxes:
        link_tag = box.select_one('.text a.title')
        
        if link_tag:
            relative_url = link_tag.get('href')
            name_fallback = link_tag.text.strip()
            event_url = relative_url if relative_url.startswith('http') else main_url.rstrip('/') + relative_url

            print(f"-> Processing event at: {event_url}")
            
            try:
                event_response = requests.get(event_url)
                event_response.raise_for_status()
            except requests.exceptions.RequestException as e:
                print(f"   Error fetching event page {event_url}: {e}")
                continue

            event_soup = BeautifulSoup(event_response.content, 'html.parser')
            
            # --- START: EXTRACTION LOGIC REFINED BASED ON SIDEBAR HTML ---
            name = name_fallback 
            date_full = "N/A"
            start_time = "N/A"

            # 1. Extract Event Name: Use the HTML <title> for reliability
            title_tag = event_soup.select_one('title')
            if title_tag:
                 name = title_tag.text.split(' - ')[0].strip()
            
            # 2. Extract Date and Time from the reliable sidebar elements
            detail_items = event_soup.select('.sidebar-event-detail')
            
            for item in detail_items:
                key_tag = item.select_one('.sidebar-event-key')
                value_tag = item.select_one('.sidebar-event-value')
                
                if key_tag and value_tag:
                    key = key_tag.text.strip().lower()
                    value = value_tag.text.strip()

                    if "date" in key:
                        date_full = value
                    elif "start time" in key:
                        start_time = value
            
            # --- END: EXTRACTION LOGIC REFINED BASED ON SIDEBAR HTML ---

            event_details.append({
                "Name": name,
                "Full Date": date_full,
                "Start Time": start_time,
                "URL": event_url
            })
            
            print(f"   Name: {name}")
            print(f"   Date: {date_full}")
            print(f"   Time: {start_time}")
            print("-" * 50)


    return event_details, None

# --- 3. FORMATTING AND EMAIL LOGIC (New) ---
from datetime import datetime
import pytz
import uuid

def format_events_as_html(event_list):
    """Takes the list of scraped events and formats them into a clean HTML table with entropy metadata."""

    # --- ENTROPY BLOCK ---
    pacific = pytz.timezone("US/Pacific")
    generated_at = datetime.now(pacific).strftime("%a %b %d · %I:%M %p %Z")
    event_count = len(event_list) if event_list else 0

    if not event_list:
        return f"<h1>Coliseum Event Report</h1><p>No upcoming events found.</p><p>Generated at: {generated_at}</p>"

    html_body = "<html><body>"
    html_body += f"<p><b>Generated at:</b> {generated_at}<br><b>Source:</b> LA Coliseum<br><b>Events detected:</b> {event_count}</p><hr>"
    html_body += "<h1>🏟️ LA Coliseum Upcoming Events Report</h1>"
    html_body += f"<p>Found {event_count} upcoming events</p>"

    # Start the HTML table
    html_body += """
    <table border="1" cellpadding="10" cellspacing="0" style="width: 100%; border-collapse: collapse; font-family: Arial, sans-serif;">
        <thead>
            <tr style="background-color: #f2f2f2;">
                <th style="text-align: left;">Event Name</th>
                <th style="text-align: left; width: 20%;">Full Date</th>
                <th style="text-align: left; width: 15%;">Start Time</th>
                <th style="text-align: left;">Event Link</th>
            </tr>
        </thead>
        <tbody>
    """

    for event in event_list:
        # Highlight 'TBD' or missing data in orange
        time_style = "color: #ff8c00; font-weight: bold;" if "TBD" in event['Start Time'].upper() or event['Start Time'] == "N/A" else ""
        
        html_body += f"""
            <tr>
                <td><b>{event['Name']}</b></td>
                <td>{event['Full Date']}</td>
                <td style="{time_style}">{event['Start Time']}</td>
                <td><a href="{event['URL']}" target="_blank">View Event Page</a></td>
            </tr>
        """

    html_body += "</tbody></table></body></html>"
    return html_body


def send_email_with_brevo(html_content, subject):
    """Connects to the Brevo API and sends the email."""
    
    if not BREVO_API_KEY:
        print("---")
        print("ERROR: BREVO_API_KEY not found. Please set it as an environment variable.")
        print("---")
        return

    print(f"Connecting to Brevo and sending email to {RECEIVER_EMAIL}...")

    # Configure the Brevo API
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = BREVO_API_KEY

    # Create an API instance
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    
    # Define the email
    sender = {"name": SENDER_NAME, "email": SENDER_EMAIL}
    to = [{"email": RECEIVER_EMAIL, "name": RECEIVER_NAME}]
    
    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=to,
        sender=sender,
        subject=subject,
        html_content=html_content
    )

    # Send the email
    try:
        api_response = api_instance.send_transac_email(send_smtp_email)
        print("\n---")
        print("Success! Email sent via Brevo.")
        print(f"Message ID: {api_response.message_id}")
        print("---")
    except ApiException as e:
        print(f"ERROR: Failed to send email via Brevo: {e}")

# --- 4. RUN THE SCRIPT ---

if __name__ == "__main__":
    
    # 1. Scrape the data
    scraped_events, error = extract_coliseum_events(MAIN_URL)
    
    email_subject = "LA Coliseum Event Report"
    if error:
        # Send an error email if scraping fails completely
        error_html = f"<h1>🚨 Scraping Error Report</h1><p>The script failed to retrieve or parse the main event page from {MAIN_URL}.</p><p>Error details: {error}</p>"
        send_email_with_brevo(error_html, "ACTION REQUIRED: Coliseum Scraping Error")
        
    elif scraped_events is not None:
        # 2. Format the successful data
        email_body = format_events_as_html(scraped_events)
        # 3. Send the email
        send_email_with_brevo(email_body, email_subject)
        
    else:
        print("Fatal error occurred. Check logs for details. No email sent.")
