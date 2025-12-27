
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

    async def generate_player_card_async(self, player_data, rank_index):
        """Generates card (Snake Animation for Top 3, Static for others)."""
        loop = asyncio.get_event_loop()
        is_top_3 = rank_index < 3
        
        if is_top_3:
            return await loop.run_in_executor(None, self._generate_snake_animated_card_sync, player_data, rank_index)
        else:
            return await loop.run_in_executor(None, self._generate_static_card_sync, player_data, rank_index)

    def _generate_static_card_sync(self, player_data, rank_index):
        from io import BytesIO
        import discord
        
        im = self._render_base_card(player_data, rank_index)
        
        b = BytesIO()
        im.save(b, format="PNG")
        b.seek(0)
        return discord.File(b, filename=f"card_{rank_index}.png")

    def _generate_snake_animated_card_sync(self, player_data, rank_index):
        from io import BytesIO
        import discord
        from PIL import Image, ImageDraw
        import math
        
        # 1. Generate Base Image (Expensive operation, do once)
        base_im = self._render_base_card(player_data, rank_index)
        
        # 2. Setup Snake Path (Chamfered Rect)
        WIDTH = 1700
        HEIGHT = 320
        CUT = 40
        
        # Coordinates of the polygon corners
        path_nodes = [
            (0, CUT), (CUT, 0),             # Chamfer Top-Left
            (WIDTH, 0),                     # Top-Right
            (WIDTH, HEIGHT - CUT),          # Chamfer Bottom-Right Start
            (WIDTH - CUT, HEIGHT),          # Chamfer Bottom-Right End
            (0, HEIGHT),                    # Bottom-Left
            (0, CUT)                        # Loop back to start
        ]
        
        # Calculate total path length and segments
        total_length = 0
        segments = []
        for i in range(len(path_nodes)):
            p1 = path_nodes[i]
            p2 = path_nodes[(i + 1) % len(path_nodes)]
            dist = math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
            segments.append({
                'start': p1, 'end': p2, 'len': dist, 'cum_start': total_length
            })
            total_length += dist

        # Helper: Get X,Y at distance D along path
        def get_point_at_dist(d):
            d = d % total_length # Wrap around
            for seg in segments:
                if d >= seg['cum_start'] and d <= seg['cum_start'] + seg['len']:
                    local_d = d - seg['cum_start']
                    if seg['len'] == 0: return seg['start']
                    ratio = local_d / seg['len']
                    x = seg['start'][0] + (seg['end'][0] - seg['start'][0]) * ratio
                    y = seg['start'][1] + (seg['end'][1] - seg['start'][1]) * ratio
                    return (x, y)
            return path_nodes[0]

        # 3. Render Frames
        frames = []
        TOTAL_FRAMES = 24 # Smooth loop
        SNAKE_LEN = 500   # Length of the neon tail
        
        # Determine Color
        NEON_GOLD = (255, 215, 0)
        NEON_SILVER = (220, 220, 255)
        NEON_BRONZE = (205, 127, 50)
        
        snake_color = NEON_GOLD
        if rank_index == 1: snake_color = NEON_SILVER
        elif rank_index == 2: snake_color = NEON_BRONZE
        
        for i in range(TOTAL_FRAMES):
            frame = base_im.copy()
            draw = ImageDraw.Draw(frame, 'RGBA')
            
            # Head position moves forward
            head_dist = (i / TOTAL_FRAMES) * total_length
            
            # Draw Snake segments (Head to Tail)
            POINTS_COUNT = 25
            step = SNAKE_LEN / POINTS_COUNT
            
            for j in range(POINTS_COUNT):
                dist_curr = head_dist - (j * step)
                dist_prev = head_dist - ((j+1) * step)
                
                p1 = get_point_at_dist(dist_curr)
                p2 = get_point_at_dist(dist_prev)
                
                # Alpha fades from 255 (head) to 0 (tail)
                progress = 1 - (j / POINTS_COUNT)
                alpha = int(255 * (progress ** 2)) # Quadratic fade for stronger head
                width = 8 if j < 5 else 5
                
                # Draw Glow (Wide low alpha)
                draw.line([p1, p2], fill=(snake_color[0], snake_color[1], snake_color[2], int(alpha/4)), width=width+8)
                # Draw Core (Thin high alpha)
                draw.line([p1, p2], fill=(snake_color[0], snake_color[1], snake_color[2], alpha), width=width)

            # Resize to save space but keep decent quality
            frame_small = frame.resize((850, 160), Image.Resampling.LANCZOS)
            frames.append(frame_small)
            
        b = BytesIO()
        frames[0].save(b, format="GIF", save_all=True, append_images=frames[1:], duration=60, loop=0, optimize=True)
        b.seek(0)
        return discord.File(b, filename=f"card_{rank_index}.gif")

    def _render_base_card(self, player_data, rank_index):
        from PIL import Image, ImageDraw, ImageFont, ImageFilter
        import requests
        from io import BytesIO
        import random
        import discord
        import math

        # Configuration (ANIME STYLE)
        WIDTH = 1700 
        HEIGHT = 320
        
        # Colors (Vibrant Anime)
        BG_DARK = (10, 10, 20) # Deep space blue
        
        TEXT_WHITE = (255, 255, 255)
        TEXT_YELLOW = (255, 240, 100) # Super Saiyan Yellow
        TEXT_GRAY = (200, 200, 200)
        
        # Rank Colors (Bright/Magical)
        NEON_GOLD = (255, 220, 0)
        NEON_SILVER = (200, 240, 255)
        NEON_BRONZE = (255, 140, 60)
        NEON_DEFAULT = (0, 200, 255) # Energy Blue
        
        NEON_GREEN = (50, 255, 100)
        NEON_RED = (255, 80, 80)

        # Helper to load font - Using "Bangers" for Anime feel if possible, else Bold
        def load_font(name, size, font_url=None):
            import os
            if font_url:
                try:
                    r = requests.get(font_url, timeout=5)
                    if r.status_code == 200:
                        return ImageFont.truetype(BytesIO(r.content), size)
                except: pass
            
            # Fallbacks
            try: return ImageFont.truetype("arial.ttf", size)
            except: pass
            return ImageFont.load_default()

        # Fonts - Anime Style
        # BANGERS font for impact
        url_bangers = "https://github.com/google/fonts/raw/main/ofl/bangers/Bangers-Regular.ttf"
        
        font_rank_big = load_font("Bangers", 90, url_bangers) 
        font_name = load_font("Bangers", 80, url_bangers)    
        font_details = load_font("Bold", 35) # Keep readable font for details
        font_wr = load_font("Bangers", 60, url_bangers)       
        font_wl = load_font("Bold", 30) 
        font_tiny = load_font("Bold", 20) 

        # Create Canvas
        im = Image.new('RGBA', (WIDTH, HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(im, 'RGBA')

        # Determine Theme Color
        theme_color = NEON_DEFAULT
        if rank_index == 0: theme_color = NEON_GOLD
        elif rank_index == 1: theme_color = NEON_SILVER
        elif rank_index == 2: theme_color = NEON_BRONZE

        # --- A. ANIME BACKGROUND (ENERGY BURST) ---
        # 1. Base Gradient
        draw.rectangle((0,0, WIDTH, HEIGHT), fill=BG_DARK)
        
        # 2. Radial Speed Lines (Burst from Icon Position)
        # Center of burst = Left side (Icon)
        burst_x, burst_y = 300, HEIGHT // 2
        
        for i in range(0, 360, 5): # Every 5 degrees
            angle = math.radians(i)
            # Ray length
            r_start = random.randint(100, 200)
            r_end = WIDTH + 500
            
            x1 = burst_x + r_start * math.cos(angle)
            y1 = burst_y + r_start * math.sin(angle)
            x2 = burst_x + r_end * math.cos(angle)
            y2 = burst_y + r_end * math.sin(angle)
            
            # Random width and alpha for energy feel
            width = random.randint(1, 4)
            alpha = random.randint(10, 50)
            color = (theme_color[0], theme_color[1], theme_color[2], alpha)
            
            draw.line([(x1, y1), (x2, y2)], fill=color, width=width)

        # --- B. SHAPE (Simple Rect with magical border) ---
        # No more chamfer, just clean box with thick borders
        # Or keep chamfer if it fits "Mecha Anime"? Let's keep chamfer, it is cool.
        CUT = 40
        points = [
            (CUT, 0), (WIDTH, 0), (WIDTH, HEIGHT - CUT), 
            (WIDTH - CUT, HEIGHT), (0, HEIGHT), (0, CUT)
        ]
        
        # Magical Aura Glow (Soft)
        # We can't do gaussian blur easily on polygon without creating mask, skipping for perf.
        # Draw multiple semi-transparent borders
        for w in [15, 10, 5]:
            alpha = 20 + (10 * (15-w))
            draw.polygon(points, outline=(theme_color[0], theme_color[1], theme_color[2], alpha), width=w)
            
        # Hard Border
        draw.polygon(points, outline=theme_color, width=3)

        # --- C. RANK ICON & AURA ---
        icon_x = 300
        rank_info = player_data.get('last_rank')
        
        # Super Saiyan Aura (Behind Icon)
        # Draw random glowing circles
        for _ in range(5):
            rx = random.randint(-20, 20)
            ry = random.randint(-20, 20)
            rs = random.randint(220, 260)
            bbox = [icon_x+90 - rs//2 + rx, HEIGHT//2 - rs//2 + ry, icon_x+90 + rs//2 + rx, HEIGHT//2 + rs//2 + ry]
            draw.ellipse(bbox, fill=(theme_color[0], theme_color[1], theme_color[2], 30))

        if rank_info and rank_info['tier'] in self.RANK_EMBLEMS:
            try:
                url = self.RANK_EMBLEMS[rank_info['tier']]
                if not hasattr(self, '_icon_cache'): self._icon_cache = {}
                key = rank_info['tier']
                if key in self._icon_cache:
                    icon = self._icon_cache[key]
                else:
                    resp = requests.get(url, timeout=3)
                    icon = Image.open(BytesIO(resp.content)).convert("RGBA")
                    if icon.getbbox(): icon = icon.crop(icon.getbbox())
                    icon = icon.resize((220, 220), Image.Resampling.LANCZOS)
                    self._icon_cache[key] = icon
                
                final_x = (icon_x + 90) - (220 // 2)
                final_y = (HEIGHT - 220) // 2
                im.paste(icon, (final_x, final_y), icon)
            except: pass

        # --- D. RANK NUMBER (Big Impact) ---
        # Draw a "Seal" or Circle behind the number
        seal_x = 150
        seal_y = HEIGHT // 2
        seal_r = 70
        draw.ellipse((seal_x-seal_r, seal_y-seal_r, seal_x+seal_r, seal_y+seal_r), fill=(0,0,0, 150), outline=theme_color, width=4)
        
        draw.text((seal_x, seal_y), f"#{rank_index + 1}", font=font_rank_big, fill=TEXT_YELLOW, anchor="mm", stroke_width=2, stroke_fill=(0,0,0))

        # --- E. INFO & STATS ---
        name_x = icon_x + 230
        
        # Name with Outline (Anime Style)
        draw.text((name_x, 100), player_data['riot_id'], font=font_name, fill=TEXT_WHITE, anchor="lm", stroke_width=3, stroke_fill=(0,0,0))
        
        # Rank Details (Bubble)
        if rank_info:
            detail_text = f"{rank_info['tier']} {rank_info['rank']} | {rank_info['leaguePoints']} LP"
        else:
            detail_text = "UNRANKED"
        
        # Glowing text
        draw.text((name_x, 170), detail_text, font=font_details, fill=theme_color, anchor="lm")

        # --- F. WINRATE (Big Numbers) ---
        stats_x = WIDTH - 80
        if rank_info:
            wins = rank_info.get('wins', 0)
            losses = rank_info.get('losses', 0)
            total = wins + losses
            wr = (wins / total * 100) if total > 0 else 0
            
            # Big WR
            draw.text((stats_x, 100), f"{wr:.1f}%", font=font_wr, fill=TEXT_WHITE, anchor="rm", stroke_width=2, stroke_fill=theme_color)
            draw.text((stats_x, 60), "WIN RATE", font=font_tiny, fill=theme_color, anchor="rm")
            
            # W/L
            draw.text((stats_x, 160), f"{wins}W - {losses}L", font=font_wl, fill=TEXT_GRAY, anchor="rm")
            
            # Energy Bar
            bar_w = 400
            bar_h = 20
            bar_x = stats_x - bar_w
            bar_y = 210
            
            # Empty Container
            draw.rectangle((bar_x, bar_y, bar_x+bar_w, bar_y+bar_h), fill=(20, 20, 30), outline=theme_color, width=2)
            
            # Fill
            fill_w = int(bar_w * (wr / 100))
            color_bar = NEON_GREEN if wr >= 50 else NEON_RED
            draw.rectangle((bar_x+2, bar_y+2, bar_x+fill_w-2, bar_y+bar_h-2), fill=color_bar)

        return im

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

        # 2. Update Channel
        try:
            await channel.purge(limit=20)
            
            # Send Header
            await channel.send("## 🏆 CLASSEMENT SOLO/DUO DU SERVEUR\n*Mis à jour en temps réel*")
            
            # Send Card for each player
            for idx, p in enumerate(sorted_players):
                file = await self.generate_player_card_async(p, idx)
                if file:
                    await channel.send(file=file)
                else:
                    logging.error(f"Failed to generate card for {p['riot_id']}")

            logging.info("Leaderboard updated with individual cards.")
            
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
