import logging
import json
import os

class PlayerTracker:
    STATE_FILE = "tracker_state.json"

    def __init__(self, riot_client, config_players):
        self.riot_client = riot_client
        self.config_players = config_players # List of {'riot_id': 'Name#Tag'}
        self.players = {} # Key: PUUID, Value: {data}
        self.load_state()

    def load_state(self):
        if os.path.exists(self.STATE_FILE):
            try:
                with open(self.STATE_FILE, 'r') as f:
                    self.players = json.load(f)
                logging.info(f"Loaded state for {len(self.players)} players.")
            except Exception as e:
                logging.error(f"Failed to load state: {e}")
                self.players = {}

    def save_state(self):
        try:
            with open(self.STATE_FILE, 'w') as f:
                json.dump(self.players, f, indent=4)
        except Exception as e:
            logging.error(f"Failed to save state: {e}")

    def initialize_players(self):
        """Resolves PUUIDs and ensures every config player is tracked."""
        logging.info("Initializing players...")
        startup_summary = []
        
        # 1. Sync Config with State
        # We want to track everyone in config.
        for p_conf in self.config_players:
            riot_id = p_conf['riot_id']
            name, tag = riot_id.split("#") if "#" in riot_id else (riot_id, "EUW")
            
            # Check if we already have this player in state (by looping state to match riot_id? No, inefficient)
            # Better: Resolve PUUID first.
            # Optimization: Check if we have a player with this Riot ID in state (if ID matches).
            # But IDs change. PUUID is constant.
            
            # Let's resolve PUUID from API (or cache if I implemented that, but strict "resolve at start" is safer)
            puuid = self.riot_client.get_puuid_by_riot_id(name, tag)
            
            if not puuid:
                logging.error(f"Could not resolve PUUID for {riot_id}")
                continue
            
            # If new player (not in state)
            if puuid not in self.players:
                logging.info(f"New player detected: {riot_id} ({puuid})")
                
                # Fetch baseline
                matches = self.riot_client.get_match_history(puuid, count=1)
                last_match_id = matches[0] if matches else None
                
                rank_stats = self.riot_client.get_rank_stats(puuid)
                
                self.players[puuid] = {
                    "riot_id": riot_id,
                    "puuid": puuid,
                    "last_match_id": last_match_id,
                    "last_rank": rank_stats
                }
            else:
                # Update Riot ID display name just in case
                self.players[puuid]['riot_id'] = riot_id
            
            # Add to summary
            data = self.players[puuid]
            rank_str = "Unranked"
            if data['last_rank']:
                rank_str = f"{data['last_rank']['tier']} {data['last_rank']['rank']} - {data['last_rank']['leaguePoints']} LP"
            startup_summary.append(f"**{riot_id}**: {rank_str}")
            
        self.save_state()
        return startup_summary

    def check_new_matches(self):
        """Checks for new matches and returns alerts."""
        alerts = []
        
        for puuid, data in self.players.items():
            try:
                # Get latest match
                history = self.riot_client.get_match_history(puuid, count=1)
                if not history:
                    continue
                
                latest_match_id = history[0]
                
                if latest_match_id != data['last_match_id']:
                    logging.info(f"New match for {data['riot_id']}: {latest_match_id}")
                    
                    # Fetch Details
                    match_details = self.riot_client.get_match_details(latest_match_id)
                    if not match_details:
                        continue # Should not happen usually
                        
                    # Fetch New Rank
                    current_rank = self.riot_client.get_rank_stats(puuid)
                    
                    # Calculate LP Diff
                    lp_diff = None
                    last_rank = data.get('last_rank')
                    if current_rank and last_rank:
                        if current_rank['tier'] == last_rank['tier'] and current_rank['rank'] == last_rank['rank']:
                            lp_diff = current_rank['leaguePoints'] - last_rank['leaguePoints']
                    
                    # Prepare Alert
                    alerts.append({
                        "player": data, # contains riot_id, puuid
                        "match": match_details,
                        "rank": current_rank,
                        "lp_diff": lp_diff
                    })
                    
                    # Update State IN MEMORY (Save happens at end of batch to be safe or per item?)
                    # If we crash, we might re-alert. Better to update memory now, save later.
                    data['last_match_id'] = latest_match_id
                    data['last_rank'] = current_rank
                    
            except Exception as e:
                logging.error(f"Error checking {data['riot_id']}: {e}")
        
        if alerts:
            self.save_state()
            
        return alerts
