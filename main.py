import json
import os
import logging
from dotenv import load_dotenv

from riot_client import RiotClient
from tracker import PlayerTracker
from discord_bot import LeagueDiscordBot

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

def main():
    # Load env if present (optional)
    load_dotenv()
    
    # Load config
    try:
        config = load_config()
    except FileNotFoundError:
        logging.error("config.json not found!")
        return
    
    # Get Credentials
    # Check config first, then env vars
    riot_api_key = config.get('riot_api_key') or os.getenv('RIOT_API_KEY')
    discord_token = config.get('discord_bot_token') or os.getenv('DISCORD_BOT_TOKEN')
    channel_id = config.get('discord_channel_id')
    
    if not riot_api_key or "YOUR_RIOT" in riot_api_key:
        logging.error("Riot API Key is missing or default in config.json")
        return
        
    if not discord_token or "YOUR_DISCORD" in discord_token:
        logging.error("Discord Token is missing or default in config.json")
        return
        
    if not channel_id:
        logging.error("Discord Channel ID is missing in config.json")
        return

    # Initialize Components
    riot_client = RiotClient(riot_api_key)
    tracker = PlayerTracker(riot_client, config['players'])
    # Parse Args
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--one-shot", action="store_true", help="Run once and exit (for Cron/GitHub Actions)")
    args = parser.parse_args()

    # Initialize Bot
    bot = LeagueDiscordBot(token=discord_token, channel_id=int(channel_id), tracker=tracker, one_shot=args.one_shot)
    
    # Run Bot
    bot.run(discord_token)

if __name__ == "__main__":
    main()
