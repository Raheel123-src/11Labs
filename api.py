from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import time
import requests
import json
from dotenv import load_dotenv
from typing import Optional, List, Dict
from browser_use_download import get_browser_use_download_url
from fastapi.middleware.cors import CORSMiddleware
from browser_use_agent_download_url import extract_download_url_from_agent, extract_download_button_headers
from elevenlabs_download import download_elevenlabs_history_audio
import boto3
from botocore.exceptions import ClientError
import datetime

# Load environment variables
load_dotenv()

app = FastAPI(title="ElevenLabs TTS Enhancement API", version="1.0.0")

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ScriptRequest(BaseModel):
    script: str
    voice_id: Optional[str] = None

class ScriptResponse(BaseModel):
    enhanced_script: Optional[str] = None
    audio_url: Optional[str] = None
    audio_file_path: Optional[str] = None
    audio_id: Optional[str] = None
    latest_history_item_id: Optional[str] = None
    browser_use_download_url: Optional[str] = None
    agent_ui_download_url: Optional[str] = None
    agent_ui_download_button_headers: Optional[list[dict[str, str]]] = None
    elevenlabs_downloaded_audio_path: Optional[str] = None
    s3_audio_url: Optional[str] = None
    task_id: str
    status: str
    message: str

def create_task(instructions: str, api_key: str):
    url = 'https://api.browser-use.com/api/v1/run-task'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    response = requests.post(url, headers=headers, json={'task': instructions})
    if response.status_code != 200:
        print("Status code:", response.status_code)
        print("Response text:", response.text)
    response.raise_for_status()
    return response.json()['id']

def get_task_details(task_id: str, api_key: str):
    url = f'https://api.browser-use.com/api/v1/task/{task_id}'
    headers = {'Authorization': f'Bearer {api_key}'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def wait_for_completion(task_id: str, api_key: str, poll_interval: int = 3, timeout_minutes: int = 10):
    start_time = time.time()
    timeout_seconds = timeout_minutes * 60
    
    while True:
        # Check if we've exceeded the timeout
        if time.time() - start_time > timeout_seconds:
            raise Exception(f"Task timed out after {timeout_minutes} minutes")
            
        details = get_task_details(task_id, api_key)
        status = details['status']
        print(f"Task status: {status}")
        if status in ['finished', 'failed', 'stopped']:
            return details
        time.sleep(poll_interval)

def download_file(url, save_path):
    response = requests.get(url)
    response.raise_for_status()
    with open(save_path, 'wb') as f:
        f.write(response.content)
    print(f"Downloaded file to {save_path}")

def get_latest_history_item_id():
    api_key = os.getenv('ELEVENLABS_API_KEY')
    if not api_key:
        raise Exception('ELEVENLABS_API_KEY is not set in the environment.')
    url = 'https://api.elevenlabs.io/v1/history'
    headers = {
        'xi-api-key': api_key,
        'Accept': 'application/json'
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    latest_item_id = data.get('history', [{}])[0].get('history_item_id')
    print(f'🆕 Latest history_item_id: {latest_item_id}')
    return latest_item_id

def upload_file_to_s3(file_path, bucket, object_name, expiration=3600):
    s3_client = boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_DEFAULT_REGION')
    )
    try:
        s3_client.upload_file(file_path, bucket, object_name)
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': object_name},
            ExpiresIn=expiration
        )
        return url
    except ClientError as e:
        print(f"S3 upload error: {e}")
        return None

def get_elevenlabs_history_ids() -> list:
    api_key = os.getenv('ELEVENLABS_API_KEY')
    if not api_key:
        print('ELEVENLABS_API_KEY is not set in the environment.')
        return []
    url = 'https://api.elevenlabs.io/v1/history'
    headers = {
        'xi-api-key': api_key,
        'Accept': 'application/json'
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return [item.get('history_item_id') for item in data.get('history', []) if 'history_item_id' in item]
    except Exception as e:
        print(f'Error fetching ElevenLabs history: {e}')
        return []

@app.post("/enhance-script/", response_model=ScriptResponse)
async def enhance_script(request: ScriptRequest):
    try:
        # Get environment variables
        api_key = os.getenv('BROWSER_USE_API_KEY')
        elevenlabs_email = os.getenv('ELEVENLABS_EMAIL')
        elevenlabs_password = os.getenv('ELEVENLABS_PASSWORD')
        env_voice_id = os.getenv('VOICE_ID')  # Get voice_id from environment as fallback
        
        if not api_key:
            raise HTTPException(status_code=500, detail="BROWSER_USE_API_KEY is not set in the environment.")
        if not elevenlabs_email or not elevenlabs_password:
            raise HTTPException(status_code=500, detail="ELEVENLABS_EMAIL and ELEVENLABS_PASSWORD must be set in the environment.")

        # Use voice_id from request, or fallback to environment variable
        voice_id_to_use = request.voice_id if request.voice_id else env_voice_id
        
        # Debug: Print which voice ID is being used
        print(f"Using voice ID: {voice_id_to_use}")
        print(f"Script length: {len(request.script)} characters")
        
        # Build instructions for task 1 (audio generation)
        if voice_id_to_use:
            voice_selection = f"first, click on the voice dropdown and select the voice with ID '{voice_id_to_use}', wait for the voice to be selected, then "
        else:
            voice_selection = ""
        
        instructions_task1 = (
            f"Go to https://elevenlabs.io/app/speech-synthesis/text-to-speech, "
            f"if redirected to login or signup, log in using email: {elevenlabs_email} and password: {elevenlabs_password}, "
            f"after successful login, go to the text-to-speech section, "
            f"{voice_selection}"
            f"paste the following script EXACTLY as provided into the text input area (do not modify, shorten, or change the script in any way): \"{request.script}\", "
            "click the 'Enhance (alpha)' button, "
            "wait for the enhanced script to appear in the text area, "
            "verify that the enhanced script contains the full original content, "
            "click the 'Generate speech' button, "
            "wait for the audio to be generated, "
            "do not download or fetch the audio file yet."
        )

        # Fetch history before task 1
        history_before = get_elevenlabs_history_ids()

        # Task 1 logic remains unchanged
        print("Creating task 1 (audio generation)...")
        task1_id = create_task(instructions_task1, api_key)
        print(f"Task 1 created with ID: {task1_id}")
        print("Waiting for task 1 completion...")
        details = wait_for_completion(task1_id, api_key, timeout_minutes=20)
        print("Task 1 completed!")

        # Process the results from task 1
        enhanced_script = None
        audio_id = None
        message = "Audio generated and uploaded to S3."

        # Try to extract enhanced script from output
        steps = details.get('steps', [])
        output_text = details.get('output', '')
        enhanced_script = None
        if output_text and len(output_text) > len(request.script):
            enhanced_script = output_text
            print(f"Found enhanced script in main output: {len(enhanced_script)} characters")
        if not enhanced_script:
            for i, step in enumerate(steps):
                step_output = step.get('output', '')
                if step_output and len(step_output) > len(request.script):
                    enhanced_script = step_output
                    print(f"Found enhanced script in step {i}: {len(enhanced_script)} characters")
                    break
        if not enhanced_script:
            for step in steps:
                step_output = step.get('output', '')
                if step_output and len(step_output) > 50 and any(word in step_output.lower() for word in ['enhanced', 'script', 'text']):
                    enhanced_script = step_output
                    print(f"Found potential enhanced script: {len(enhanced_script)} characters")
                    break
        if enhanced_script:
            print(f"Final enhanced script length: {len(enhanced_script)} characters")
        else:
            print("No enhanced script found in output")
            enhanced_script = output_text  # Fallback to main output

        # Try to extract the audio's unique id from the steps using the selector
        audio_id = None
        for step in steps:
            step_output = step.get('output', '')
            import re
            match = re.search(r'<button[^>]*data-type=["\ ](list-item-trigger-overlay)["\ ][^>]*id=["\ ]([\w-]+)["\ ]', step_output)
            if match:
                audio_id = match.group(2)
                print(f"Found audio_id: {audio_id}")
                break

        # Fetch history before task 1
        history_before = get_elevenlabs_history_ids()

        # Poll for new history item
        latest_history_item_id = None
        poll_start = datetime.datetime.now()
        max_wait = 30  # seconds
        while (datetime.datetime.now() - poll_start).total_seconds() < max_wait:
            history_after = get_elevenlabs_history_ids()
            new_ids = [hid for hid in history_after if hid not in history_before]
            if new_ids:
                latest_history_item_id = new_ids[0]
                print(f"New history item found: {latest_history_item_id}")
                break
            time.sleep(2)
        if not latest_history_item_id:
            print("No new history item found after polling, falling back to most recent.")
            history_after = get_elevenlabs_history_ids()
            if history_after:
                latest_history_item_id = history_after[0]

        # Download the audio file to /uploads
        elevenlabs_downloaded_audio_path = None
        if latest_history_item_id:
            os.makedirs('uploads', exist_ok=True)
            audio_filename = f"{latest_history_item_id}.mp3"
            audio_path = os.path.join('uploads', audio_filename)
            success = download_elevenlabs_history_audio(latest_history_item_id, audio_path)
            if success:
                elevenlabs_downloaded_audio_path = audio_path
                print(f"Downloaded ElevenLabs audio to {audio_path}")
            else:
                print(f"Failed to download ElevenLabs audio for history id {latest_history_item_id}")

        # Upload to S3
        s3_audio_url = None
        if elevenlabs_downloaded_audio_path and os.path.exists(elevenlabs_downloaded_audio_path):
            s3_bucket = os.getenv('S3_BUCKET_NAME')
            s3_folder = os.getenv('S3_AUDIO_FOLDER', '')
            import pathlib
            file_name = pathlib.Path(elevenlabs_downloaded_audio_path).name
            s3_key = f"{s3_folder}{file_name}" if s3_folder else file_name
            s3_audio_url = upload_file_to_s3(elevenlabs_downloaded_audio_path, s3_bucket, s3_key)
            if s3_audio_url:
                print(f"S3 download link: {s3_audio_url}")

        return ScriptResponse(
            enhanced_script=enhanced_script,
            audio_url=None,
            audio_file_path=None,
            audio_id=audio_id,
            latest_history_item_id=latest_history_item_id,
            browser_use_download_url=None,
            agent_ui_download_url=None,
            agent_ui_download_button_headers=None,
            elevenlabs_downloaded_audio_path=elevenlabs_downloaded_audio_path,
            s3_audio_url=s3_audio_url,
            task_id=task1_id,
            status=details.get('status', 'unknown'),
            message="Audio generated and uploaded to S3."
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing script: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "ElevenLabs TTS Enhancement API is running"}

@app.get("/")
async def root():
    return {
        "message": "ElevenLabs TTS Enhancement API",
        "endpoints": {
            "enhance_script": "/enhance-script/",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 