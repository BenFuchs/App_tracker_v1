import psutil
import time
from datetime import datetime
import logging
import getpass
import os
import datetime as dt
import os.path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# If modifying these SCOPES, delete the token.json file.
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Setup logging
logging.basicConfig(filename='vscode_usage_and_process.log',
                    level=logging.DEBUG,
                    format='%(asctime)s - %(message)s',
                    filemode='a')  # Changed to append mode
logger = logging.getLogger(__name__)

# Get the current user's username
current_user = getpass.getuser()

# Function to get VSCode process
def get_vscode_process():
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            # Tracking the "code" process (adjust if necessary)
            if 'code helper' in proc.info['name'].lower():
                return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return None

def create_event(start_time, end_time):
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                logger.error("credentials.json file not found.")
                return
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)

    event = {
        'summary': 'VSCode Coding Session',
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': 'Asia/Jerusalem',  # Change to your timezone
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': 'Asia/Jerusalem',  # Change to your timezone
        }
    }

    try:
        event_result = service.events().insert(calendarId='primary', body=event).execute()
        logger.info(f"Event created: {event_result.get('htmlLink')}")
    except Exception as e:
        logger.error(f"Failed to create event: {e}")

def track_application_close():
    vscode_process = None
    open_time = None

    try:
        while True:
            current_vscode_process = get_vscode_process()
            if current_vscode_process:
                if not vscode_process:
                    # New VSCode process detected, start timing
                    vscode_process = current_vscode_process
                    open_time = datetime.now()
                    logger.info(f"VSCode opened at {open_time}")
                    print(f"vscode tracking started at {open_time}")
            else:
                if vscode_process:
                    # VSCode just closed
                    close_time = datetime.now()
                    if open_time:
                        usage_time = close_time - open_time
                        logger.info(f"VSCode closed at {close_time}, Total time open: {usage_time}")
                        print(f"vscode tracking ended at {close_time}, total time open: {usage_time}")
                        # Create an event in Google Calendar
                        create_event(open_time, close_time)
                    else:
                        logger.warning("VSCode closed but open_time is not set.")
                    vscode_process = None  # Reset the process tracker
            time.sleep(5)  # Check every 5 seconds to reduce CPU usage
    except KeyboardInterrupt:
        logger.info("Tracking closed applications stopped.")

if __name__ == "__main__":
    track_application_close()
