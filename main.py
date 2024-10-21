import requests
import time
from atproto import Client
import logging
from datetime import datetime
import random


# TfL API endpoint
TFL_API_URL = "https://api.tfl.gov.uk/Line/Mode/tube,overground,dlr,tram/Status"

# Bluesky credentials (replace with your own)
BLUESKY_USERNAME = "username.bsky.social"
BLUESKY_PASSWORD = "app_password"

# Dictionary to store the most recent status for each line
last_status = {}


def get_tfl_status():
    response = requests.get(TFL_API_URL)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching TfL status: {response.status_code}")
        return None

def process_tfl_data(data):
    updates = []
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for line in data:
        line_name = line['name']
        line_status = line['lineStatuses'][0]
        status = line_status['statusSeverityDescription']
        
        # Check if the status has changed
        if line_name not in last_status or last_status[line_name] != status:
            if status != "Good Service":
                update = f"{current_time}\n{line_name}: {status}"
                
                # Add reason if available
                if 'reason' in line_status:
                    update += f"\n{line_status['reason']}"
                
                # Add disruption info if available
                for disruption in line.get('disruptions', []):
                    if 'description' in disruption:
                        update += f"\n{disruption['description']}"
                
                # Truncate the update if it's too long
                if len(update) > 300:
                    update = update[:297] + "..."
                
                updates.append(update)
            
            # Update the last known status for this line
            last_status[line_name] = status
    
    return updates

def post_to_bluesky(client, update):
    client.send_post(text=update)

def main():
    logging.info("TfL Bot started")
    bluesky_client = Client()
    retry_delay = 1
    max_retry_delay = 3600  # Maximum delay of 1 hour

    while True:
        try:
            bluesky_client.login(BLUESKY_USERNAME, BLUESKY_PASSWORD)
            logging.info("Successfully logged in to Bluesky")
            retry_delay = 1  # Reset delay on successful login
            break
        except Exception as e:
            logging.error(f"Failed to log in to Bluesky: {str(e)}")
            retry_delay = min(retry_delay * 2 + random.uniform(0, 1), max_retry_delay)
            logging.info(f"Retrying in {retry_delay} seconds")
            time.sleep(retry_delay)

    while True:
        try:
            tfl_data = get_tfl_status()
            if tfl_data:
                updates = process_tfl_data(tfl_data)
                for update in updates:
                    post_to_bluesky(bluesky_client, update)
                    logging.info(f"Posted update: {update}")
            
            # Wait for 5 minutes before checking again
            time.sleep(300)
        except Exception as e:
            logging.error(f"An error occurred: {str(e)}")
            time.sleep(60)  # Wait a minute before trying again

if __name__ == "__main__":
    main()
