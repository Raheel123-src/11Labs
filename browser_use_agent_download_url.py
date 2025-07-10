import requests
from bs4 import BeautifulSoup, Tag
from typing import Optional, Dict, List

def extract_download_url_from_agent(agent_url: str) -> Optional[str]:
    """
    Given a Browser Use agent page URL, fetch the page, parse the HTML, and extract the download URL from the headers of the download button.
    Returns the download URL if found, else None.
    """
    try:
        response = requests.get(agent_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        # Find all buttons
        buttons = soup.find_all('button')
        for button in buttons:
            if not isinstance(button, Tag):
                continue
            # Check if button has a data-download-url attribute
            if button.has_attr('data-download-url'):
                val = button.get('data-download-url')
                if isinstance(val, str) and val.startswith('http'):
                    return val
            # Check for custom attributes or headers
            for attr, attr_val in button.attrs.items():
                if 'download' in attr and isinstance(attr_val, str) and attr_val.startswith('http'):
                    return attr_val
            # Sometimes the URL is in the button's text or a child element
            if button.text and 'download' in button.text.lower():
                # Try to find a link inside the button
                link = button.find('a', href=True)
                if link and isinstance(link, Tag):
                    href = link.get('href')
                    if isinstance(href, str) and href.startswith('http'):
                        return href
        # If not found, try to find any link with download in the text
        links = soup.find_all('a', href=True)
        for link in links:
            if not isinstance(link, Tag):
                continue
            if 'download' in link.text.lower():
                href = link.get('href')
                if isinstance(href, str) and href.startswith('http'):
                    return href
        return None
    except Exception as e:
        print(f"Error extracting download URL: {e}")
        return None

def extract_download_button_headers(agent_url: str) -> Optional[List[Dict[str, str]]]:
    """
    Given a Browser Use agent page URL, fetch the page, parse the HTML, and extract all attributes (headers) from every button.
    Returns a list of dictionaries of attributes for each button found.
    """
    try:
        response = requests.get(agent_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        # Find all buttons
        buttons = soup.find_all('button')
        all_button_headers = []
        for button in buttons:
            if not isinstance(button, Tag):
                continue
            # Collect all attributes for this button
            attrs_dict = {str(attr): str(val) for attr, val in button.attrs.items()}
            all_button_headers.append(attrs_dict)
        return all_button_headers if all_button_headers else None
    except Exception as e:
        print(f"Error extracting download button headers: {e}")
        return None 