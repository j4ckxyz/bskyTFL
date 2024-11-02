import time
import requests
from atproto import Client
import logging
import json
from datetime import datetime, timezone
from pathlib import Path

# Set up logging to console
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Bluesky credentials
BLUESKY_USERNAME = "username.bsky.socialk"
BLUESKY_PASSWORD = "app_password"

# TfL API endpoint
TFL_API_URL = "https://api.tfl.gov.uk/Line/Mode/tube,overground,dlr,elizabeth-line/Status"

# Initialize Bluesky client
client = Client()
client.login(BLUESKY_USERNAME, BLUESKY_PASSWORD)

# Add constants for post tracking
POSTS_LOG_FILE = 'tfl_posts.json'

def load_posted_statuses():
    try:
        with open(POSTS_LOG_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {'posts': []}

def save_posted_status(message, posted_time):
    posted_statuses = load_posted_statuses()
    posted_statuses['posts'].append({
        'text': message,
        'timestamp': posted_time.isoformat()
    })
    
    # Keep only last 100 posts
    posted_statuses['posts'] = posted_statuses['posts'][-100:]
    
    with open(POSTS_LOG_FILE, 'w') as f:
        json.dump(posted_statuses, f)

def is_already_posted(message):
    posted_statuses = load_posted_statuses()
    current_time = datetime.now(timezone.utc)
    
    # Check for exact message match within the last hour (3600 seconds)
    return any(
        post['text'] == message and 
        (current_time - datetime.fromisoformat(post['timestamp'])).total_seconds() < 3600  # 1 hour window
        for post in posted_statuses['posts']
    )

def get_tfl_status():
    try:
        response = requests.get(TFL_API_URL, timeout=10)  # Added timeout
        if response.status_code == 200:
            return response.json()
        else:
            logging.error(f"Error fetching TfL status: {response.status_code}")
            return None
    except requests.RequestException as e:
        logging.error(f"Request failed: {e}")
        return None

def post_to_bluesky(message):
    try:
        if not is_already_posted(message):
            client.send_post(text=message)
            save_posted_status(message, datetime.now(timezone.utc))
            logging.info(f"Posted to Bluesky: {message}")
            return True
        else:
            logging.info(f"Skipping duplicate post: {message}")
            return False
    except Exception as e:
        logging.error(f"Error posting to Bluesky: {e}")
        return False

def main():
    while True:
        try:
            status_data = get_tfl_status()
            if status_data:
                current_issues = []
                
                for line in status_data:
                    line_name = line['name']
                    status = line['lineStatuses'][0]['statusSeverityDescription']
                    
                    if status != "Good Service":
                        message = f"{line_name}: {status}"
                        if not is_already_posted(message):
                            current_issues.append(message)
                
                # Post all current issues in a single message if possible
                if current_issues:
                    combined_message = "\n".join(current_issues)
                    if len(combined_message) <= 300:  # Bluesky character limit
                        post_to_bluesky(combined_message)
                    else:
                        # If too long, post individually
                        for message in current_issues:
                            post_to_bluesky(message)
            
            time.sleep(300)  # 5 minute delay
            
        except Exception as e:
            logging.error(f"Error in main loop: {e}")
            time.sleep(60)  # Wait a minute before retrying if there's an error

if __name__ == '__main__':
    main()
