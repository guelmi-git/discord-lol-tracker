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
    # PRIORITY: Environment Variables (GitHub Secrets) > Config File (Local)
    
    riot_api_key = os.getenv('RIOT_API_KEY')
    if not riot_api_key:
        val = config.get('riot_api_key')
        if val and "YOUR_RIOT" not in val:
            riot_api_key = val

    discord_token = os.getenv('DISCORD_BOT_TOKEN')
    if not discord_token:
        val = config.get('discord_bot_token')
        if val and "YOUR_DISCORD" not in val:
            discord_token = val

    channel_id_str = os.getenv('DISCORD_CHANNEL_ID')
    if not channel_id_str:
        val = config.get('discord_channel_id')
        if val and str(val) != "YOUR_CHANNEL_ID":
            channel_id_str = str(val)

    # Validation
    if not riot_api_key:
        logging.error("CRITICAL: Riot API Key is missing! Set RIOT_API_KEY env var or update config.json")
        return # Exit
        
    if not discord_token:
        logging.error("CRITICAL: Discord Token is missing! Set DISCORD_BOT_TOKEN env var or update config.json")
        return # Exit
        
    if not channel_id_str:
        logging.error("CRITICAL: Discord Channel ID is missing!")
        return # Exit

    logging.info(f"Credentials loaded. Channel ID: {channel_id_str}")

    # Initialize Components
    try:
        riot_client = RiotClient(riot_api_key)
        tracker = PlayerTracker(riot_client, config['players'])
        
        # Parse Args
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--one-shot", action="store_true", help="Run once and exit (for Cron/GitHub Actions)")
        args = parser.parse_args()

        # Initialize Bot
        logging.info("Initializing Discord Bot...")
        bot = LeagueDiscordBot(token=discord_token, channel_id=int(channel_id_str), tracker=tracker, one_shot=args.one_shot)
        
        # Run Bot
        logging.info("Starting Bot execution...")
        bot.run(discord_token)
    except Exception as e:
        logging.exception("CRITICAL ERROR DURING EXECUTION:")
        raise e

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.critical("Unhandled exception in main:")
        import traceback
        traceback.print_exc()
        import sys
        sys.exit(1)
