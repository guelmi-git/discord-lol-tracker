
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

    def __init__(self, token, channel_id, tracker, one_shot=False, config=None):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.token = token
        self.channel_id = int(channel_id)
        self.tracker = tracker
        self.one_shot = one_shot
        self.config = config or {}
        
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

            # Initial Leaderboard Update
            await self.update_leaderboard()


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
                
                if alerts:
                    for alert in alerts:
                        # Find participant info for the player
                        p_data = alert['player']
                        match = alert['match']
                        # Find the participant dict for this player's PUUID
                        participant = next((p for p in match['info']['participants'] if p['puuid'] == p_data['puuid']), None)
                        
                        if participant:
                            embed, file_attachment = await self.create_match_embed(p_data, match, participant, alert['rank'], alert['lp_diff'])
                            if channel:
                                await channel.send(embed=embed, file=file_attachment)
                            else:
                                logging.error("Channel not available for sending alert.")
                    
                    # Update Leaderboard after a batch of alerts
                    await self.update_leaderboard()
            except asyncio.TimeoutError:
                logging.error("Tracker check timed out! Skipping this cycle.")
            except Exception as e:
                logging.error(f"Error in polling loop: {e}")
            
            if self.one_shot:
                logging.info("One-shot mode finished. Exiting.")
                await self.close()
                break
                
            await asyncio.sleep(120) # 2 minutes
    
    async def generate_leaderboard_image_async(self, sorted_players):
        """Generates the leaderboard image in a non-blocking way."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._generate_leaderboard_image_sync, sorted_players)

    def _generate_leaderboard_image_sync(self, sorted_players):
        from PIL import Image, ImageDraw, ImageFont
        import requests
        from io import BytesIO

        # --- CONFIGURATION (UPDATED FOR VISIBILITY) ---
        WIDTH = 1200
        HEADER_HEIGHT = 140
        CARD_HEIGHT = 180 # Taller cards for bigger text
        PADDING = 20
        GAP = 20
        
        # Colors (High Contrast)
        BG_COLOR = (5, 5, 10)     # Almost Black
        CARD_BG = (30, 32, 45)    # Distinct Dark Blue-Grey
        TEXT_WHITE = (255, 255, 255)
        TEXT_GRAY = (200, 200, 200) # Lighter Grey for readability
        
        # Accents
        NEON_CYAN = (0, 255, 255)
        NEON_GOLD = (255, 223, 0)
        NEON_SILVER = (224, 224, 224)
        NEON_BRONZE = (205, 127, 50)
        NEON_RED = (255, 80, 80)
        NEON_GREEN = (80, 255, 120)

        total_height = HEADER_HEIGHT + (len(sorted_players) * (CARD_HEIGHT + GAP)) + PADDING

        # Helper to load font
        def load_font(name, size):
            try:
                # Orbitron for futuristic look
                url = f"https://github.com/google/fonts/raw/main/ofl/orbitron/Orbitron-{name}.ttf"
                r = requests.get(url, timeout=5)
                return ImageFont.truetype(BytesIO(r.content), size)
            except:
                return ImageFont.load_default()

        # BIGGER FONTS
        font_header = load_font("Black", 70)
        font_rank_big = load_font("Bold", 60)
        font_name = load_font("Bold", 55) # HUGE NAME
        font_stats = load_font("Regular", 36) # Readable Stats
        font_small = load_font("Regular", 24)

        # Create Canvas
        im = Image.new('RGBA', (WIDTH, total_height), BG_COLOR)
        draw = ImageDraw.Draw(im)

        # --- HEADER ---
        # Draw a top neon bar
        draw.rectangle((0, 0, WIDTH, 15), fill=NEON_CYAN)
        
        # Title
        title_text = "LEADERBOARD"
        # Shadow / Glow
        draw.text((WIDTH//2 + 3, HEADER_HEIGHT//2 + 3), title_text, font=font_header, fill=(0, 100, 100), anchor="mm")
        draw.text((WIDTH//2, HEADER_HEIGHT//2), title_text, font=font_header, fill=NEON_CYAN, anchor="mm")

        # --- PLAYERS ---
        for idx, p in enumerate(sorted_players):
            y_start = HEADER_HEIGHT + (idx * (CARD_HEIGHT + GAP))
            y_end = y_start + CARD_HEIGHT
            
            # 1. Card Background
            border_color = (60, 60, 80) 
            if idx == 0: border_color = NEON_GOLD
            elif idx == 1: border_color = NEON_SILVER
            elif idx == 2: border_color = NEON_BRONZE
            
            # Card Body
            draw.rounded_rectangle((PADDING, y_start, WIDTH - PADDING, y_end), radius=20, fill=CARD_BG, outline=None)
            
            # Left Accent (Thicker)
            draw.rounded_rectangle((PADDING, y_start, PADDING + 15, y_end), radius=20, fill=border_color, corners=(True, False, False, True))

            # 2. Position Number
            pos_text = f"#{idx + 1}"
            draw.text((PADDING + 80, y_start + CARD_HEIGHT//2), pos_text, font=font_rank_big, fill=border_color, anchor="mm")

            rank_data = p.get('last_rank')
            
            # 3. Rank Icon (LARGE)
            icon_x = PADDING + 160
            if rank_data and rank_data['tier'] in self.RANK_EMBLEMS:
                try:
                    url = self.RANK_EMBLEMS[rank_data['tier']]
                    resp = requests.get(url, timeout=5)
                    icon = Image.open(BytesIO(resp.content)).convert("RGBA")
                    
                    if icon.getbbox(): icon = icon.crop(icon.getbbox())
                    
                    # 140px Icon
                    target_icon_h = 140
                    icon_final = icon.resize((target_icon_h, target_icon_h), Image.Resampling.LANCZOS)
                    
                    icon_y = y_start + (CARD_HEIGHT - target_icon_h) // 2
                    im.paste(icon_final, (icon_x, icon_y), icon_final)
                except Exception as e:
                    logging.error(f"Failed to load rank icon: {e}")
            
            # 4. Player Name
            name_x = icon_x + 160
            draw.text((name_x, y_start + 55), p['riot_id'], font=font_name, fill=TEXT_WHITE, anchor="lm")
            
            # 5. Rank Text
            if rank_data:
                # "Emerald II"
                tier_str = f"{rank_data['tier'].title()} {rank_data['rank']}"
                # "50 LP"
                lp_str = f"{rank_data['leaguePoints']} LP"
                
                full_rank = f"{tier_str} • {lp_str}"
                draw.text((name_x, y_start + 115), full_rank, font=font_stats, fill=border_color, anchor="lm")
            else:
                draw.text((name_x, y_start + 115), "Unranked", font=font_stats, fill=TEXT_GRAY, anchor="lm")

            # 6. Win/Loss Stats (Aligned Right)
            if rank_data:
                wins = rank_data.get('wins', 0)
                losses = rank_data.get('losses', 0)
                total = wins + losses
                wr = (wins / total * 100) if total > 0 else 0
                
                stats_x = WIDTH - PADDING - 40
                
                # WR % (Top Right of Card)
                draw.text((stats_x, y_start + 60), f"{wr:.1f}% WR", font=font_name, fill=TEXT_WHITE, anchor="rm")  # Using big font for WR too
                
                # W/L (Below)
                wl_str = f"{wins}W - {losses}L"
                draw.text((stats_x, y_start + 110), wl_str, font=font_stats, fill=TEXT_GRAY, anchor="rm")
                
                # Bar at very bottom of card right side? Or maybe under WR.
                # Let's put a glow bar under the textual stats
                bar_w = 200
                bar_h = 8
                bar_x = stats_x - bar_w
                bar_y = y_start + 140
                
                draw.rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), fill=(40, 40, 50))
                fill_w = int(bar_w * (wr / 100))
                color_bar = NEON_GREEN if wr >= 50 else NEON_RED
                draw.rectangle((bar_x, bar_y, bar_x + fill_w, bar_y + bar_h), fill=color_bar)

        # Output
        b = BytesIO()
        im.save(b, format="PNG")
        b.seek(0)
        return discord.File(b, filename="leaderboard_futuristic_v2.png")

    async def update_leaderboard(self):
        """Updates the leaderboard channel with the current ranking."""
        leaderboard_channel_id = self.config.get("DISCORD_LEADERBOARD_CHANNEL_ID")
        if not leaderboard_channel_id:
            return

        try:
            channel = self.get_channel(int(leaderboard_channel_id))
            if not channel:
                try:
                    channel = await self.fetch_channel(int(leaderboard_channel_id))
                except Exception:
                    logging.error(f"Could not find Leaderboard Channel {leaderboard_channel_id}")
                    return
        except ValueError:
            logging.error("Invalid Leaderboard Channel ID config")
            return

        # 1. Get & Sort Players
        players_data = list(self.tracker.players.values())
        
        # Helper for sorting
        TIER_VALUES = {
            "CHALLENGER": 9000, "GRANDMASTER": 8000, "MASTER": 7000,
            "DIAMOND": 5000, "EMERALD": 4000, "PLATINUM": 3000,
            "GOLD": 2000, "SILVER": 1000, "BRONZE": 500, "IRON": 0,
            "UNRANKED": -1
        }
        ROMAN_VALUES = {"I": 4, "II": 3, "III": 2, "IV": 1}

        def rank_key(p):
            rank_info = p.get('last_rank')
            if not rank_info: return -1
            tier_score = TIER_VALUES.get(rank_info['tier'], 0)
            division_score = ROMAN_VALUES.get(rank_info['rank'], 0) * 100
            lp = rank_info['leaguePoints']
            if tier_score >= 7000: return tier_score + lp
            return tier_score + division_score + lp

        sorted_players = sorted(players_data, key=rank_key, reverse=True)

        # 2. Generate Image
        file = await self.generate_leaderboard_image_async(sorted_players)
        
        # 3. Clean & Send
        try:
            await channel.purge(limit=10)
            if file:
                await channel.send(file=file)
            else:
                 await channel.send("Impossible de générer le classement (Erreur interne).")
            logging.info("Leaderboard updated.")
        except Exception as e:
            logging.error(f"Failed to update leaderboard: {e}") 

            

    
    async def combine_images_async(self, champion_id, rank_tier):
        """Downloads Champion Icon and Rank Emblem, stacks them vertically, and returns a discord.File."""
        try:
            # Run blocking image processing in executor
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._combine_images_sync, champion_id, rank_tier)
        except Exception as e:
            logging.error(f"Failed to combine images: {e}")
            return None

    def _combine_images_sync(self, champion_id, rank_tier):
        from PIL import Image, ImageOps, ImageDraw
        import requests
        from io import BytesIO

        # Helper to treat images
        def crop_transparency(img):
            bbox = img.getbbox()
            if bbox:
                return img.crop(bbox)
            return img

        def add_corners(im, rad):
            circle = Image.new('L', (rad * 2, rad * 2), 0)
            draw = ImageDraw.Draw(circle)
            draw.ellipse((0, 0, rad * 2, rad * 2), fill=255)
            alpha = Image.new('L', im.size, 255)
            w, h = im.size
            alpha.paste(circle.crop((0, 0, rad, rad)), (0, 0))
            alpha.paste(circle.crop((0, rad, rad, rad * 2)), (0, h - rad))
            alpha.paste(circle.crop((rad, 0, rad * 2, rad)), (w - rad, 0))
            alpha.paste(circle.crop((rad, rad, rad * 2, rad * 2)), (w - rad, h - rad))
            im.putalpha(alpha)
            return im

        # 1. Download Champion Icon
        champ_url = f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-icons/{champion_id}.png"
        resp_champ = requests.get(champ_url)
        img_champ = Image.open(BytesIO(resp_champ.content)).convert("RGBA")
        
        # Resize Champion to a fixed good quality size
        target_width = 256
        img_champ = img_champ.resize((target_width, target_width), Image.Resampling.LANCZOS)
        
        # Apply Modern Rounded Corners to Champion
        # Creating a rounded rectangle mask
        mask = Image.new("L", (target_width, target_width), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle((0, 0, target_width, target_width), radius=40, fill=255)
        
        # Apply mask
        img_champ_rounded = Image.new("RGBA", (target_width, target_width))
        img_champ_rounded.paste(img_champ, (0, 0), mask=mask)
        img_champ = img_champ_rounded

        # 2. Download Rank Emblem
        img_rank = None
        if rank_tier in self.RANK_EMBLEMS:
            rank_url = self.RANK_EMBLEMS[rank_tier]
            resp_rank = requests.get(rank_url)
            img_rank = Image.open(BytesIO(resp_rank.content)).convert("RGBA")
            
            # CRITICAL: Crop transparent borders to avoid "tiny image" effect
            img_rank = crop_transparency(img_rank)

        if not img_rank:
            # Just return champion image as file
            b = BytesIO()
            img_champ.save(b, format="PNG")
            b.seek(0)
            return discord.File(b, filename="combined.png")

        # 3. Resize Rank to match Champion Width (maintain aspect ratio)
        # We want the rank to be the same width as the champion icon (256px)
        base_width = target_width
        w_percent = (base_width / float(img_rank.width))
        h_size = int((float(img_rank.height) * float(w_percent)))
        img_rank = img_rank.resize((base_width, h_size), Image.Resampling.LANCZOS)

        # 4. Create Composite Image (Vertical Stack with spacing)
        spacing = 10
        total_height = img_champ.height + img_rank.height + spacing
        combined = Image.new("RGBA", (base_width, total_height))
        
        combined.paste(img_champ, (0, 0), img_champ)
        combined.paste(img_rank, (0, img_champ.height + spacing), img_rank)

        # 5. Save to Bytes
        output_buffer = BytesIO()
        combined.save(output_buffer, format="PNG")
        output_buffer.seek(0)
        
        return discord.File(output_buffer, filename="combined.png")

    async def create_match_embed(self, player_data, match_info, participant_info, rank_info, lp_diff):
        """Creates a modern 'Pro/Esport' style embed for the match result"""
        win = participant_info['win']
        game_duration = match_info['info'].get('gameDuration', 0)
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
            generic_roast = random.choice(self.DEFEAT_MESSAGES)
            specific_roast = None
            cham_key = champion_name
            if cham_key not in self.CHAMPION_ROASTS:
                 cham_key = champion_name.replace(" ", "")
            
            if cham_key in self.CHAMPION_ROASTS:
                specific_roast = random.choice(self.CHAMPION_ROASTS[cham_key])
            
            if specific_roast:
                flavor_text = random.choice([generic_roast, specific_roast])
            else:
                flavor_text = generic_roast

        embed = discord.Embed(title=title, description=f"*{flavor_text}*", color=color)
        
        # 2. Author (Player Name)
        riot_id = f"{player_data['riot_id']}"
        embed.set_author(name=f"{riot_id} • Ranked Solo/Duo", icon_url="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png")

        # 3. Stats Line (KDA, CS)
        kills = participant_info['kills']
        deaths = participant_info['deaths']
        assists = participant_info['assists']
        kda_calc = (kills + assists) / max(1, deaths)
        cs = participant_info['totalMinionsKilled'] + participant_info.get('neutralMinionsKilled', 0)
        
        stats_line = f"**{kills}/{deaths}/{assists}** (KDA: {kda_calc:.2f}) • **{cs} CS**"
        embed.add_field(name="Performance", value=stats_line, inline=False)

        # 4. Rank & LP
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
        
        # 5. Visuals - Composite Image
        champ_id = participant_info.get('championId')
        file_attachment = None
        
        if champ_id:
             # Generate the combined image (Champion + Rank)
             file_attachment = await self.combine_images_async(champ_id, tier)
             if file_attachment:
                 embed.set_thumbnail(url="attachment://combined.png")

        # Footer
        embed.set_footer(text=f"Match Duration: {minutes}m {seconds}s")
        
        return embed, file_attachment
