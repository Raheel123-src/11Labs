import os
import time
import requests
import json
from dotenv import load_dotenv

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

def wait_for_completion(task_id: str, api_key: str, poll_interval: int = 3):
    while True:
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

def main():
    load_dotenv()
    api_key = os.getenv('BROWSER_USE_API_KEY')
    elevenlabs_email = os.getenv('ELEVENLABS_EMAIL')
    elevenlabs_password = os.getenv('ELEVENLABS_PASSWORD')
    voice_id = os.getenv('VOICE_ID')
    if not api_key:
        raise ValueError('BROWSER_USE_API_KEY is not set in the environment.')
    if not elevenlabs_email or not elevenlabs_password:
        raise ValueError('ELEVENLABS_EMAIL and ELEVENLABS_PASSWORD must be set in the environment.')
    if not voice_id:
        raise ValueError('VOICE_ID must be set in the environment (your custom ElevenLabs voice id).')

    script = input("Enter the script you want to enhance and convert to speech:\n")

    instructions = (
        f"Go to https://elevenlabs.io/app/speech-synthesis/text-to-speech, "
        f"if redirected to login or signup, log in using email: {elevenlabs_email} and password: {elevenlabs_password}, "
        f"after successful login, go to the text-to-speech section, "
        f"select the voice with id '{voice_id}', "
        f"paste the following script into the input: \"{script}\", "
        "click the 'Enhance (alpha)' button, "
        "wait for the enhanced script to appear, "
        "click the 'Generate speech' button, "
        "wait for the audio to be generated, "
        "then click the download button for the generated audio file, download it, and return it as an output file. If you cannot download, return the direct download link to the audio file, and also return the enhanced script."
    )
    print("Creating task...")
    task_id = create_task(instructions, api_key)
    print(f"Task created with ID: {task_id}")
    print("Waiting for task completion...")
    details = wait_for_completion(task_id, api_key)
    print("Task completed!")
    # Try to download the mp3 if present
    output_files = details.get('output_files', [])
    os.makedirs('uploads', exist_ok=True)
    found_mp3 = False
    for file_info in output_files:
        # If file_info is a dict (with 'name' and 'url')
        if isinstance(file_info, dict):
            name = file_info.get('name', '')
            url = file_info.get('url', '')
        # If file_info is a string (assume it's a URL)
        elif isinstance(file_info, str):
            name = os.path.basename(file_info)
            url = file_info
        else:
            continue
        # Only download if url looks like a valid http(s) link
        if (name.endswith('.mp3') or url.endswith('.mp3')) and url.startswith('http'):
            save_path = os.path.join('uploads', name)
            download_file(url, save_path)
            found_mp3 = True
    if not found_mp3:
        # Try to extract a direct audio link from output or steps
        output_text = details.get('output', '')
        steps = details.get('steps', [])
        import re
        url_pattern = r'https?://[\w./\-_%]+\.mp3(\?[^\s"]*)?'
        match = re.search(url_pattern, output_text)
        if not match:
            for step in steps:
                step_output = step.get('output', '')
                match = re.search(url_pattern, step_output)
                if match:
                    break
        if match:
            print(f"Direct audio file link: {match.group(0)}")
        else:
            print("No downloadable mp3 file found. Please check the output for more details.")
    print(json.dumps(details, indent=2))

if __name__ == '__main__':
    main() 