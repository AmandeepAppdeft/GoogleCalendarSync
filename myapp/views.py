from django.http import JsonResponse
from .basic_working import calendar_updated  # Import the function from execute_script.py
from django.views.decorators.csrf import csrf_exempt
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import uuid
import base64
from datetime import datetime

TOKEN_FILE_PATH = './token.json'
SCOPES = ['https://www.googleapis.com/auth/calendar']

def generate_unique_id():
    # Generate a UUID and encode it in base64 to get a URL-safe string
    generated_uuid = uuid.uuid4()
    encoded_uuid = base64.urlsafe_b64encode(generated_uuid.bytes).decode('utf-8').rstrip('=')

    # Get the current timestamp and format it
    current_time = datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]

    # Concatenate the encoded UUID and timestamp to create the Channel ID
    unique_id = f"{encoded_uuid}{current_time}"
    return unique_id

unique_channel_id = generate_unique_id()


def load_credentials():
    creds = None
    if os.path.exists(TOKEN_FILE_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE_PATH)
    
    return creds

def authenticate():
    flow = InstalledAppFlow.from_client_secrets_file(
        './credentials.json', SCOPES)
    
    # Use localhost instead of 5001 to avoid port conflicts
    creds = flow.run_local_server(port=8001)

    # Save the credentials for the next run
    with open(TOKEN_FILE_PATH, 'w') as token:
        token.write(creds.to_json())

    return creds


existing_channel_ids = set()  # Maintain a set to store existing channel IDs

def is_channel_id_unique(channel_id):
    return channel_id not in existing_channel_ids

@csrf_exempt
def execute_script(request):
    global unique_channel_id, existing_channel_ids

    if request.method == 'POST':
        creds = load_credentials()

        if not creds or not creds.valid:
            creds = authenticate()

        unique_channel_id = generate_unique_id()

        # Ensure the channel ID is unique within a reasonable number of attempts
        max_attempts = 5
        attempts = 0

        while not is_channel_id_unique(unique_channel_id) and attempts < max_attempts:
            unique_channel_id = generate_unique_id()
            attempts += 1

        if attempts == max_attempts:
            return JsonResponse({'error': 'Failed to generate a unique channel ID'})

        existing_channel_ids.add(unique_channel_id)
        result = calendar_updated(creds, unique_channel_id)

        if result == 0:
            # Assuming calendar_updated was successful, attempt to remove the channel ID
            if unique_channel_id in existing_channel_ids:
                existing_channel_ids.remove(unique_channel_id)
            return JsonResponse({'message': 'Success'})
        else:
            # If there was an error, remove the ID if it exists in the set
            if unique_channel_id in existing_channel_ids:
                existing_channel_ids.remove(unique_channel_id)
            return JsonResponse({'error': 'Calendar update failed'})

    return JsonResponse({'error': 'POST request required'})


# @csrf_exempt
# def execute_script(request):
#     global unique_channel_id  # Ensure the uniqueness check for channel ID

#     if request.method == 'POST':
#         creds = load_credentials()

#         if not creds or not creds.valid:
#             creds = authenticate()
            
#         if is_channel_id_unique(unique_channel_id):
#             existing_channel_ids.add(unique_channel_id)  # Add the channel ID to the set
#             calendar_updated(creds, unique_channel_id)  # Process calendar update

#         return JsonResponse({'message': 'Success'})

#     else:
#         return JsonResponse({'error': 'POST request required'})
    