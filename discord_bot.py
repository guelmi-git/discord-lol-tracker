
import discord
from discord.ext import tasks
import logging
import asyncio
import random

class LeagueDiscordBot(discord.Client):
    RANK_EMBLEMS = {
        "IRON": "https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-emblem/emblem-iron.png",
        "BRONZE": "https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-emblem/emblem-bronze.png",
        "SILVER": "https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-emblem/emblem-silver.png",
        "GOLD": "https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-emblem/emblem-gold.png",
        "PLATINUM": "https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-emblem/emblem-platinum.png",
        "EMERALD": "https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-emblem/emblem-emerald.png",
        "DIAMOND": "https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-emblem/emblem-diamond.png",
        "MASTER": "https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-emblem/emblem-master.png",
        "GRANDMASTER": "https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-emblem/emblem-grandmaster.png",
        "CHALLENGER": "https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-emblem/emblem-challenger.png"
    }

    VICTORY_MESSAGES = [
        "Bien joué GOAT, continue comme ça !",
        "Trop facile pour toi, monte le niveau !",
        "LE ROI EST DANS LA PLACE 👑",
        "Masterclass, rien à dire.",
        "C'est ça qu'on veut voir ! 🚀"
    ]

    DEFEAT_MESSAGES = [
        "Allez concentre toi un peu, ça devient gênant un niveau si pitoyable...",
        "FF 15 la prochaine fois ?",
        "C'est pas possible de jouer comme ça...",
        "Ton équipe te déteste, sache-le.",
        "Reprends-toi ou désinstalle le jeu. 🚮"
    ]

    def __init__(self, token, channel_id, tracker, one_shot=False):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.token = token
        self.channel_id = int(channel_id)
        self.tracker = tracker
        self.one_shot = one_shot
        
        # Load Roasts
        try:
             import json
             with open('roasts.json', 'r', encoding='utf-8') as f:
                 self.CHAMPION_ROASTS = json.load(f)
             logging.info(f"Loaded {len(self.CHAMPION_ROASTS)} champion roasts.")
        except Exception as e:
             logging.error(f"Failed to load roasts.json: {e}")
             self.CHAMPION_ROASTS = {}

        # Load Praises
        try:
             with open('praises.json', 'r', encoding='utf-8') as f:
                 self.CHAMPION_PRAISES = json.load(f)
             logging.info(f"Loaded {len(self.CHAMPION_PRAISES)} champion praises.")
        except Exception as e:
             logging.error(f"Failed to load praises.json: {e}")
             self.CHAMPION_PRAISES = {}

    async def on_ready(self):
        logging.info(f'Logged in as {self.user} (ID: {self.user.id})')
        
        # Verify channel visibility
        channel = self.get_channel(self.channel_id)
        if not channel:
            logging.error(f"Channel {self.channel_id} not found! Listing visible channels:")
            for guild in self.guilds:
                for ch in guild.text_channels:
                    logging.info(f" - {ch.name} ({ch.id}) in {guild.name}")

        else:
            logging.info(f"Target Channel '{channel.name}' found.")
            
            # Initialize Tracker (Sync method running in executor)
            loop = asyncio.get_event_loop()
            logging.info('Initializing tracker...')
            summary = await loop.run_in_executor(None, self.tracker.initialize_players)
            
            # Send summary if available (for both one-shot and continuous)
            if summary:
                 desc = "✅ **Tracking activé ! Classement actuel :**\n" + "\n".join(summary)
                 await channel.send(embed=discord.Embed(title="Bot Started", description=desc, color=discord.Color.blue()))


        logging.info('Tracker initialized. Starting polling loop.')
        self.loop.create_task(self.polling_loop())

    async def polling_loop(self):
        await self.wait_until_ready()
        channel = self.get_channel(self.channel_id)
        
        while not self.is_closed():
            logging.info("Checking for new matches...")
            try:
                # Run the check with a strict timeout of 60 seconds (Script runs every 120s locally or once on GH)
                # On GH, we want it to die fast if stuck.
                loop = asyncio.get_event_loop()
                alerts = await asyncio.wait_for(
                    loop.run_in_executor(None, self.tracker.check_new_matches),
                    timeout=60.0 # 60 seconds max
                )
                
                for alert in alerts:
                    # Find participant info for the player
                    p_data = alert['player']
                    match = alert['match']
                    # Find the participant dict for this player's PUUID
                    participant = next((p for p in match['info']['participants'] if p['puuid'] == p_data['puuid']), None)
                    
                    if participant:
                        embed = self.create_match_embed(p_data, match, participant, alert['rank'], alert['lp_diff'])
                        if channel:
                            await channel.send(embed=embed)
                        else:
                            logging.error("Channel not available for sending alert.")
            
            except asyncio.TimeoutError:
                logging.error("Tracker check timed out! Skipping this cycle.")
            except Exception as e:
                logging.error(f"Error in polling loop: {e}")
            
            if self.one_shot:
                logging.info("One-shot mode finished. Exiting.")
                await self.close()
                break
                
            await asyncio.sleep(120) # 2 minutes
    
    def create_match_embed(self, player_data, match_info, participant_info, rank_info, lp_diff):
        """Creates a modern 'Pro/Esport' style embed for the match result"""
        win = participant_info['win']
        game_duration = match_info['info'].get('gameDuration', 0) # Access gameDuration from 'info'
        minutes = game_duration // 60
        seconds = game_duration % 60
        
        # 1. Colors & Title
        color = 0x57F287 if win else 0xED4245 # Discord Green or Red
        outcome = "VICTORY" if win else "DEFEAT"
        champion_name = participant_info['championName']
        title = f"{'🏆' if win else '💀'} {outcome} as {champion_name}"

        # Flavor Text
        if win:
            # Contextual Praise Logic
            generic_praise = random.choice(self.VICTORY_MESSAGES)
            specific_praise = None
            
            cham_key = champion_name
            if cham_key not in self.CHAMPION_PRAISES:
                 cham_key = champion_name.replace(" ", "")
            
            if cham_key in self.CHAMPION_PRAISES:
                specific_praise = random.choice(self.CHAMPION_PRAISES[cham_key])
            
            if specific_praise:
                flavor_text = random.choice([generic_praise, specific_praise])
            else:
                flavor_text = generic_praise
        else:
            # Contextual Roast Logic:
            # We want to mix Generic Taunts and Champion Specific Taunts (if available).
            # To ensure variety ("alterné"), we pick randomly between the two categories with equal weight.
            
            # 1. Pick a random generic message
            generic_roast = random.choice(self.DEFEAT_MESSAGES)
            
            # 2. Pick a random specific message (if exists)
            specific_roast = None
            # Handle spaces/casing just in case (e.g. "Lee Sin" vs "LeeSin" key in json)
            # My JSON has keys like "LeeSin", "MissFortune" (PascalCase no space) or "Lee Sin"? 
            # Let's check my JSON content... I wrote "LeeSin", "MissFortune" etc?
            # Actually I wrote "LeeSin". But `champion_name` comes from API.
            # API usually gives "LeeSin" as ID, but "Lee Sin" as name...
            # Wait, `champion_name` in `create_match_embed` comes from `participant_info['championName']`.
            # In MatchV5, `championName` is usually the ID (e.g. "MonkeyKing" for Wukong, "LeeSin" for Lee Sin).
            # So direct key lookup should work if my keys match MatchV5 IDs.
            # I used standard names in JSON. Let's try direct look up, if fail try removing spaces.
            
            cham_key = champion_name
            if cham_key not in self.CHAMPION_ROASTS:
                 # Try removing spaces
                 cham_key = champion_name.replace(" ", "")
            
            if cham_key in self.CHAMPION_ROASTS:
                specific_roast = random.choice(self.CHAMPION_ROASTS[cham_key])
            
            # 3. Choose between them
            # If specific exists, 50% chance of each. Else 100% generic.
            if specific_roast:
                flavor_text = random.choice([generic_roast, specific_roast])
            else:
                flavor_text = generic_roast

        embed = discord.Embed(title=title, description=f"*{flavor_text}*", color=color)
        
        # 2. Author (Player Name)
        riot_id = f"{player_data['riot_id']}"
        embed.set_author(name=f"{riot_id} • Ranked Solo/Duo", icon_url="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png") # Placeholder icon or bot icon

        # 3. Stats Line (KDA, CS)
        kills = participant_info['kills']
        deaths = participant_info['deaths']
        assists = participant_info['assists']
        kda_calc = (kills + assists) / max(1, deaths)
        cs = participant_info['totalMinionsKilled'] + participant_info.get('neutralMinionsKilled', 0)
        
        stats_line = f"**{kills}/{deaths}/{assists}** (KDA: {kda_calc:.2f}) • **{cs} CS**"
        embed.add_field(name="Performance", value=stats_line, inline=False)

        # 4. Rank & LP (The 'Pro' Visual)
        tier = rank_info['tier'] if rank_info else "UNRANKED"
        rank = rank_info['rank'] if rank_info else ""
        lp = rank_info['leaguePoints'] if rank_info else 0
        
        rank_str = f"{tier} {rank} - {lp} LP"
        
        if lp_diff is not None and lp_diff != 0:
            emoji = "📈" if lp_diff > 0 else "📉"
            sign = "+" if lp_diff > 0 else ""
            lp_diff_str = f"**{sign}{lp_diff} LP** {emoji}"
            rank_display = f"{rank_str}\n{lp_diff_str}"
        else:
            rank_display = f"{rank_str}"

        embed.add_field(name="Rank Update", value=rank_display, inline=True)
        
        # 5. Visuals
        # Thumbnail: Champion Icon (Restored)
        champ_id = participant_info.get('championId')
        if champ_id:
            champ_icon_url = f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-icons/{champ_id}.png"
            embed.set_thumbnail(url=champ_icon_url)

        # Image: Rank Emblem (Bigger)
        # Note: Rank emblems might be large, but this makes them very visible as requested.
        if tier in self.RANK_EMBLEMS:
            embed.set_image(url=self.RANK_EMBLEMS[tier])
        
        # Footer
        embed.set_footer(text=f"Match Duration: {minutes}m {seconds}s")
        
        return embed
