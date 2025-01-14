import requests
from datetime import datetime
import time
import smtplib
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv
import json
import logging

logging.basicConfig(level=logging.DEBUG)

class GlobalEntryChecker:
    def __init__(self, location_id="5001", target_date=None, check_interval=300):
        """
        Initialize the appointment checker
        location_id: The ID for Salt Lake City location
        target_date: Date string in format 'YYYY-MM-DD' before which to look for appointments
        check_interval: Time between checks in seconds (default 5 minutes)
        """
        self.base_url = "https://ttp.cbp.dhs.gov/schedulerapi/locations/{}/slots?minimum=1"
        self.location_id = location_id
        self.target_date = datetime.strptime(target_date, '%Y-%m-%d') if target_date else None
        self.check_interval = check_interval
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Load environment variables for email configuration
        load_dotenv()
        self.email_sender = os.environ.get('EMAIL_SENDER')
        self.email_password = os.environ.get('EMAIL_PASSWORD')
        self.email_recipient = os.environ.get('EMAIL_RECIPIENT')

    def check_appointments(self):
        """Check for available appointments"""
        try:
            url = self.base_url.format(self.location_id)
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            # The API returns a single appointment object, not a list
            appointment = response.json()
            
            if not appointment:
                print(f"No appointments found at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                return None
            
            # Convert the single appointment into a list for consistent processing
            appointments = [appointment]
            available_slots = []
            
            for slot in appointments:
                if 'timestamp' not in slot:
                    continue
                    
                slot_date = datetime.strptime(slot['timestamp'].split('T')[0], '%Y-%m-%d')
                if not self.target_date or slot_date <= self.target_date:
                    available_slots.append({
                        'startTimestamp': slot['timestamp'],
                        'active': slot.get('active', 0),
                        'total': slot.get('total', 0)
                    })
            
            if available_slots:
                for slot in available_slots:
                    print(f"Found slots on: {slot['startTimestamp']}, Active: {slot['active']}, Total: {slot['total']}")
            
            return available_slots

        except requests.exceptions.RequestException as e:
            print(f"Error checking appointments: {e}")
            return None

    def send_notification(self, appointments):
        """Send email notification about available appointments"""
        if not all([self.email_sender, self.email_password, self.email_recipient]):
            print("Email configuration missing. Please check your .env file.")
            return

        try:
            msg_text = "Available Global Entry Appointments:\n\n"
            for apt in appointments:
                msg_text += f"Date: {apt['startTimestamp']}\n"
                msg_text += f"Active Slots: {apt['active']}\n"
                msg_text += f"Total Slots: {apt['total']}\n\n"
            
            msg = MIMEText(msg_text)
            msg['Subject'] = 'Global Entry Appointment Available!'
            msg['From'] = self.email_sender
            msg['To'] = self.email_recipient

            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
                smtp_server.login(self.email_sender, self.email_password)
                smtp_server.sendmail(self.email_sender, self.email_recipient, msg.as_string())
            
            print("Notification email sent successfully!")

        except Exception as e:
            print(f"Error sending email notification: {e}")

    def run(self):
        """Modified to run once when using GitHub Actions"""
        print(f"Starting Global Entry appointment checker for Salt Lake City...")
        print(f"Looking for appointments before: {self.target_date.strftime('%Y-%m-%d') if self.target_date else 'No date limit'}")
        
        # Remove the while True loop for GitHub Actions
        appointments = self.check_appointments()
        
        if appointments:
            print(f"Found {len(appointments)} available appointments!")
            self.send_notification(appointments)

if __name__ == "__main__":
    # Example usage
    checker = GlobalEntryChecker(
        target_date="2025-05-01",  # Change this to your desired date
        check_interval=600  # Checks every 5 minutes
    )
    checker.run()