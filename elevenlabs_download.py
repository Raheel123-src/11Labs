import os
import requests
from dotenv import load_dotenv

load_dotenv()

def download_elevenlabs_history_audio(history_item_id: str, save_path: str) -> bool:
    api_key = os.getenv('ELEVENLABS_API_KEY')
    if not api_key:
        print('ELEVENLABS_API_KEY is not set in the environment.')
        return False
    url = f'https://api.elevenlabs.io/v1/history/{history_item_id}/audio'
    headers = {
        'xi-api-key': api_key,
        'Accept': 'audio/mpeg'
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            f.write(response.content)
        print(f'Audio downloaded to {save_path}')
        return True
    except Exception as e:
        print(f'Error downloading audio: {e}')
        return False

if __name__ == "__main__":
    # Example usage
    history_item_id = input("Enter history_item_id: ")
    save_path = input("Enter path to save audio (e.g. output.mp3): ")
    download_elevenlabs_history_audio(history_item_id, save_path) 