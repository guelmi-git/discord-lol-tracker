import requests

urls = {
    "GOLD": "https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-emblem/emblem-gold.png",
    "CHAMP": "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-icons/1.png"
}

for k, url in urls.items():
    try:
        r = requests.head(url)
        print(f"{k}: {r.status_code}")
    except Exception as e:
        print(f"{k}: Error {e}")
