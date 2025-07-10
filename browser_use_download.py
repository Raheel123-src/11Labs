import os
import requests
import re

def get_browser_use_download_url(task_id: str, api_key: str):
    url = f'https://api.browser-use.com/api/v1/task/{task_id}'
    headers = {'Authorization': f'Bearer {api_key}'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    details = response.json()
    # Try output_files first
    output_files = details.get('output_files', [])
    for file_info in output_files:
        if isinstance(file_info, dict):
            url = file_info.get('url', '')
        elif isinstance(file_info, str):
            url = file_info
        else:
            continue
        if url.endswith('.mp3') or url.endswith('.wav'):
            return url
    # Try to extract from steps or output
    steps = details.get('steps', [])
    output_text = details.get('output', '')
    url_pattern = r'https?://[\w./\-_%]+\.(mp3|wav)(\?[^\s"]*)?'
    match = re.search(url_pattern, output_text)
    if not match:
        for step in steps:
            step_output = step.get('output', '')
            match = re.search(url_pattern, step_output)
            if match:
                break
    if match:
        return match.group(0)
    return None 