import json
import requests
import os
from riot_client import RiotClient

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

def debug_rank():
    config = load_config()
    api_key = config['riot_api_key']
    
    # Init client (Defaults to EUW1)
    client = RiotClient(api_key)
    
    # Pick first player
    player = config['players'][0]
    riot_id = player['riot_id']
    print(f"--- Debugging {riot_id} ---")
    
    # 1. Get PUUID
    name, tag = riot_id.split('#')
    puuid = client.get_puuid_by_riot_id(name, tag)
    print(f"PUUID: {puuid}")
    
    if not puuid:
        print("Failed to get PUUID")
        return

    # 2. Get Summoner
    summoner = client.get_summoner_by_puuid(puuid)
    print(f"Summoner Data: {summoner}")
    
    if not summoner:
        print("Failed to get Summoner")
        return
        
    summoner_id = summoner['id']
    print(f"Summoner ID: {summoner_id}")
    
    # 3. Get League Entries (RAW)
    url = f"https://euw1.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
    headers = {"X-Riot-Token": api_key}
    print(f"Fetching: {url}")
    
    resp = requests.get(url, headers=headers)
    print(f"Status Code: {resp.status_code}")
    print("Raw Response:")
    print(json.dumps(resp.json(), indent=2))

if __name__ == "__main__":
    debug_rank()
