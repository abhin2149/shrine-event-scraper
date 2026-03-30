🏟️ Event Automation & Notification System

A collection of automated scripts that scrape, process, and deliver
event data for multiple venues and USC athletics programs. The system
aggregates schedules, detects updates, and sends formatted email reports
via Brevo (Sendinblue).

------------------------------------------------------------------------

📌 Overview

This repository contains automation scripts for:

🏟️ Venue Event Tracking

-   Shrine Auditorium
-   LA Memorial Coliseum
-   BMO Stadium
-   Expo Park / WTC

🎓 USC Athletics

-   Men’s Basketball
-   Women’s Basketball
-   Men’s & Women’s Volleyball
-   Additional USC sports schedules

Each script: - Fetches data from official APIs or schedule pages
- Parses and normalizes event/game information
- Formats results into structured HTML emails
- Sends automated notifications via Brevo API

------------------------------------------------------------------------

⚙️ Features

-   Automated data scraping (HTML + JSON APIs)
-   Unified HTML email formatting (table-based layouts)
-   Timezone-aware date/time handling (PT conversion where applicable)
-   Event status detection (active/cancelled)
-   Academic/season year handling for sports schedules
-   Error reporting via email alerts
-   Secure API key usage via environment variables
-   Modular scripts per venue/sport for easy maintenance

------------------------------------------------------------------------

🚀 How It Works

1.  Fetch Data
    -   APIs (JSON endpoints) or HTML pages are queried using requests
2.  Parse & Normalize
    -   Data is extracted using BeautifulSoup (HTML scraping) and JSON
        parsing
    -   dateutil.parser for datetime handling
3.  Transform
    -   Events/games are standardized into:
        -   Title
        -   Date
        -   Time
        -   Location
        -   Status / Result
4.  Format
    -   HTML emails using tables for sports schedules
    -   Structured layouts for event listings
5.  Send Email
    -   Emails are sent using Brevo API (sib_api_v3_sdk)
    -   Includes optional metadata headers

------------------------------------------------------------------------

📧 Email Delivery

All notifications are sent via Brevo (Sendinblue).

Required Environment Variable:

BREVO_API_KEY=your_api_key_here

Example configuration:

SENDER_EMAIL = “your@email.com” RECEIVER_EMAIL = “recipient@email.com”

------------------------------------------------------------------------

🧾 Example Use Cases

-   Daily automated email of USC sports games
-   Monitoring Shrine / BMO / Coliseum events
-   Detecting newly added or removed events
-   Internal reporting snapshots
-   Scheduling awareness automation

------------------------------------------------------------------------

▶️ Running a Script

Each script can be run independently:

python shrine_events.py 
python usc_volleyball.py

------------------------------------------------------------------------

🔐 Security Best Practices

-   Store API keys in environment variables
-   Avoid committing sensitive credentials
-   Use .env files locally if needed
-   Restrict API key permissions

------------------------------------------------------------------------

🧩 Extending the System

1.  Create a new script
2.  Implement:
    -   Data fetching
    -   Parsing
    -   Formatting
    -   Email sending
3.  Optionally integrate into a centralized runner

------------------------------------------------------------------------

📊 Suggested Improvements

-   Centralized orchestration
-   Deduplication / change detection
-   Database storage
-   Slack/SMS integrations
-   Web dashboard
-   Logging & monitoring
-   Retry logic

------------------------------------------------------------------------

🧠 Design Philosophy

-   Modular per venue/sport
-   Consistent output formats
-   Simple and reliable libraries
-   Maintainable and readable code

------------------------------------------------------------------------

📬 Contact

Maintained by: Abhinav Vadhera (vadhera@usc.edu)
