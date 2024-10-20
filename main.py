import requests
import time
from atproto import Client
import logging
from datetime import datetime


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
                    update += f"\nReason: {line_status['reason']}"
                
                # Add URL if available
                if 'url' in line_status:
                    update += f"\nMore info: {line_status['url']}"
                
                updates.append(update)
            
            # Update the last known status for this line
            last_status[line_name] = status
    
    return updates

def post_to_bluesky(client, update):
    client.send_post(text=update)

def main():
    bluesky_client = Client()
    bluesky_client.login(BLUESKY_USERNAME, BLUESKY_PASSWORD)

    
    tfl_data = get_tfl_status()
    if tfl_data:
        process_tfl_data(tfl_data)
    
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
