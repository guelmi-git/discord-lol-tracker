import logging
from riotwatcher import LolWatcher, ApiError

class RiotClient:
    def __init__(self, api_key, region='euw1', routing_value='europe'):
        self.api_key = api_key
        self.watcher = LolWatcher(api_key)
        self.region = region            # e.g., 'euw1' for Summoner/League V4
        self.routing_value = routing_value # e.g., 'europe' for Match V5 / Account V1

    def get_puuid_by_riot_id(self, game_name, tag_line):
        """Fetches PUUID using Account V1 via direct requests (riotwatcher issue workaround)"""
        import requests
        try:
            url = f"https://{self.routing_value}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
            headers = {"X-Riot-Token": self.api_key} # Access key explicitly
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()['puuid']
            else:
                logging.error(f"Riot API Error (get_puuid): {response.status_code} {response.text}")
                return None
        except Exception as err:
            logging.error(f"Riot API Error (get_puuid): {err}")
            return None

    def get_summoner_by_puuid(self, puuid):
        """Fetches Summoner V4 data via direct requests"""
        import requests
        try:
            url = f"https://{self.region}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
            headers = {"X-Riot-Token": self.api_key}
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                logging.error(f"Riot API Error (get_summoner): {response.status_code} {response.text}")
                return None
        except Exception as err:
            logging.error(f"Riot API Error (get_summoner): {err}")
            return None

    def get_rank_stats(self, puuid):
        """Fetches League V4 data (Rank, LP, Wins/Losses) via PUUID (bypassing broken SummonerID)"""
        import requests
        try:
            # Undocumented/New endpoint: entries/by-puuid/{puuid}
            url = f"https://{self.region}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
            headers = {"X-Riot-Token": self.api_key}
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                leagues = response.json()
                logging.info(f"Rank Data for {puuid}: {leagues}") # Debug log
                # Filter for RANKED_SOLO_5x5
                for league in leagues:
                    if league['queueType'] == 'RANKED_SOLO_5x5':
                        return league
                return None # Unranked or not found
            else:
                logging.error(f"Riot API Error (get_rank): {response.status_code} {response.text}")
                return None 
        except Exception as err:
            logging.error(f"Riot API Error (get_rank): {err}")
            return None

    def get_last_matches(self, puuid, count=1):
        """Fetches list of match IDs (Match V5)"""
        try:
            # filters: type='ranked' to only see ranked games? User said "Ranked Solo/Duo Queue"
            # but usually type='ranked' includes flex. Queue 420 is Solo/Duo.
            # We can filter by queue in the query or after fetching. 
            # safe to fetch generic and filter later or use queue=420.
            # Let's simple fetch latest.
            return self.watcher.match.matchlist_by_puuid(self.routing_value, puuid, count=count, queue=420) 
        except ApiError as err:
            logging.error(f"Riot API Error (get_matches): {err}")
            return []

    def get_match_details(self, match_id):
        """Fetches Match V5 details"""
        try:
            return self.watcher.match.by_id(self.routing_value, match_id)
        except ApiError as err:
            logging.error(f"Riot API Error (get_match_details): {err}")
            return None
