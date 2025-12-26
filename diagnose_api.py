import requests
import json

# Load key from config
with open('config.json', 'r') as f:
    config = json.load(f)

API_KEY = config['riot_api_key']
REGION = "euw1"
ROUTING = "europe"
RIOT_ID_NAME = "Guelmi"
RIOT_ID_TAG = "9595"

def diagnose():
    try:
        print(f"--- Diagnosing {RIOT_ID_NAME}#{RIOT_ID_TAG} ---")
        
        # 1. Account V1
        url_account = f"https://{ROUTING}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{RIOT_ID_NAME}/{RIOT_ID_TAG}"
        print(f"GET {url_account}")
        resp = requests.get(url_account, headers={"X-Riot-Token": API_KEY})
        print(f"Status: {resp.status_code}")
        
        if resp.status_code != 200:
            print(f"Error: {resp.text}")
            return

        data_account = resp.json()
        print(f"Account Data: {data_account}")
        puuid = data_account.get('puuid')
        print(f"PUUID: {puuid}")
        
        # 2. Summoner V4
        url_summoner = f"https://{REGION}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
        print(f"GET {url_summoner}")
        resp = requests.get(url_summoner, headers={"X-Riot-Token": API_KEY})
        print(f"Status: {resp.status_code}")
        print("Raw Response Body:")
        print(resp.text)
        
        data_summoner = resp.json()
        summoner_id = data_summoner.get('id')
        print(f"Summoner ID: {summoner_id}")
        
        # 3. League V4 (Testing PUUID as SummonerID)
        if not summoner_id:
            print("Trying PUUID as SummonerID...")
            summoner_id = puuid

        url_league = f"https://{REGION}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
        print(f"GET {url_league}")
        resp = requests.get(url_league, headers={"X-Riot-Token": API_KEY})
        print(f"Status: {resp.status_code}")
        print("Response: " + resp.text)
        
        # 4. League V4 (Testing Method 2: by-puuid endpoint?)
        url_league_puuid = f"https://{REGION}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
        print(f"GET {url_league_puuid}")
        resp = requests.get(url_league_puuid, headers={"X-Riot-Token": API_KEY})
        print(f"Status: {resp.status_code}")
        print("Response: " + resp.text)


    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    diagnose()
