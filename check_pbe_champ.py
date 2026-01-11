import requests
from io import BytesIO
from PIL import Image

url = "https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/champion-icons/1.png"
print(f"Testing: {url}")

try:
    r = requests.get(url)
    print(f"Status: {r.status_code}")
    print(f"Content-Type: {r.headers.get('Content-Type')}")
    print(f"Content-Length: {len(r.content)}")
    
    if r.status_code == 200:
        img = Image.open(BytesIO(r.content))
        print(f"Image Format: {img.format}")
        print(f"Image Size: {img.size}")
    else:
        print("Failed to download.")

except Exception as e:
    print(f"Error: {e}")
