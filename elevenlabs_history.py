import os
import requests
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

def get_elevenlabs_history() -> Optional[Dict[str, Any]]:
    api_key = os.getenv('ELEVENLABS_API_KEY')
    if not api_key:
        print('ELEVENLABS_API_KEY is not set in the environment.')
        return None
    url = 'https://api.elevenlabs.io/v1/history'
    headers = {
        'xi-api-key': api_key,
        'Accept': 'application/json'
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f'Error fetching ElevenLabs history: {e}')
        return None

if __name__ == "__main__":
    history = get_elevenlabs_history()
    if history:
        print("History fetched successfully:")
        print(history)
    else:
        print("Failed to fetch history.") 