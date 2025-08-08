import discord
import os
import json

def generate_embed(server: dict, context: str) -> discord.Embed:
    name = server.get("name", "Unknown Server")
    chronicle = server.get("chronicle", "Unknown")
    style = server.get("style", None)
    rates = server.get("rates", "N/A")
    votes = server.get("votes", 0)
    website = server.get("website", "#")
    discord_link = server.get("discord", "#")
    thumbnail = server.get("thumbnail", "")
    image = server.get("image", None)
    premium = server.get("premium", False)
    rank = server.get("rank", None)

    # Ανάλυση rates
    xp, sp, adena, drop = "?", "?", "?", "?"
    rate_parts = [part.strip().lower().replace("x", "") for part in rates.split("/")]

    if len(rate_parts) >= 1:
        xp = rate_parts[0]
    if len(rate_parts) >= 2:
        sp = rate_parts[1]
    if len(rate_parts) >= 3:
        adena = rate_parts[2]
    if len(rate_parts) >= 4:
        drop = rate_parts[3]

    spoil = server.get("spoil", "?")

    # Τίτλος
    if premium:
        title = f"👑 {name}"
    elif context == "leaderboard" and rank is not None:
        title = f"Rank {rank}: {name}"
    else:
        title = name

    # Χρώμα
    if premium:
        color = discord.Color.gold()
    else:
        chronicle_colors = {
            "interlude": "#1C7BB9",
            "high five": "#8552f2",
            "essence": "#016903",
            "classic": "#314507",
            "how": "#4c1ea1",
            "rod": "#4c1ea1",
            "sod": "#4c1ea1",
            "gracia final": "#f29829",
            "gracia epilogue": "#f29828",
            "freya": "#3b9cd9"
        }
        hex_code = chronicle_colors.get(chronicle.lower().strip(), "#95a5a6")
        color = discord.Color(int(hex_code.lstrip("#"), 16))

    # Features
    feature_map = {
        "auto_farm": "Auto Farm",
        "buff_store": "NPC Buffer",
        "custom_events": "Auto Events",
        "retail": "Retail Like",
        "dualbox_limit": "Multi-Box",
        "customs": "Custom Items",
        "skins": "Costumes",
        "global_gk": "Global GK",
        "multi_server": "Multi Server",
        "gm_shop": "GM Shop"
    }

    enabled_features = [label for key, label in feature_map.items() if server.get(key) is True]
    features_text = " • ".join(enabled_features) if enabled_features else "N/A"

    
    sep = "\u202F•\u202F"
    sep2 = "\u202F\u202F\u202F•\u202F\u202F\u202F"

    style_labels = {
        "pvp server": "🗡️ PvP Server",
        "craft server": "⛏️ Craft Server",
        "low rate": "🌿 Low Rates"
    }
    style_label = f"**{style_labels.get(style.lower(), style)}**" if style else ""


    # 📦 Description
    if premium:
        description = (
            f"🍁 **Chronicle:** {chronicle}\n"
            f"{style_label}\n"
            f"👍 **Votes:** {votes}\n\n"
            f"⚔️ **Rates:**\n"
            f"• XP x{xp}\n"
            f"• SP x{sp}\n"
            f"• Drop x{adena}\n"
            f"• Adena x{drop}\n"
            f"• Spoil x{spoil}\n\n"
            f"🧩 **Features:**\n" + "\n".join([f"• {f}" for f in enabled_features]) + "\n\n"
            f"📌 **More infos:**\n"
            f"🔗 **Visit:** [Website]({website}){sep2}💬 **Join:** [Server's Community]({discord_link})"
        )
    else:
        first_line = f"🍁 **Chronicle:** {chronicle}"
        if style:
            first_line += f"{sep2}{style_label}"
        first_line += f"{sep2}👍 **Votes:** {votes}"

        description = (
            f"{first_line}\n"
            f"⚔️ **Rates:** **XP** x{xp} {sep} **SP** x{sp} {sep} **Drop** x{adena} {sep} **Adena** x{drop}" + \
            (f"{sep} **Spoil** x{spoil}" if spoil else "") + "\n"
            f"🧩 **Features:** {features_text}\n"
            f"📌 **More infos:** 🔗 **Visit:** [Website]({website}){sep}💬 **Join:** [Server's Community]({discord_link})"
        )

    # Embed
    embed = discord.Embed(title=title, description=description, color=color)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    if premium and image:
        embed.set_image(url=image)


    return embed
    
VOTERS_FILE = "voters.json"

def load_voters():
    if os.path.exists(VOTERS_FILE):
        with open(VOTERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_voters(voters):
    with open(VOTERS_FILE, "w") as f:
        json.dump(voters, f)
