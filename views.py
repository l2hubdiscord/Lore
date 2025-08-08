
import discord
from discord.ui import Button, View
from utils import generate_embed
import json
from datetime import datetime, timezone
import os
from utils import load_voters, save_voters


VOTES_FILE = "votes.json"
SERVERS_FILE = "servers.json"
UNSUBSCRIBED_FILE = "unsubscribed.json"

def load_unsubscribed():
    if os.path.exists(UNSUBSCRIBED_FILE):
        with open(UNSUBSCRIBED_FILE, "r") as f:
            return json.load(f)
    return {}

def save_unsubscribed(data):
    with open(UNSUBSCRIBED_FILE, "w") as f:
        json.dump(data, f, indent=2)


def load_votes():
    if os.path.exists(VOTES_FILE):
        with open(VOTES_FILE, "r") as f:
            content = f.read().strip()
            if content:
                return json.loads(content)
    return {}

def save_votes(votes):
    with open(VOTES_FILE, "w") as f:
        json.dump(votes, f)

def load_servers():
    if os.path.exists(SERVERS_FILE):
        with open(SERVERS_FILE, "r") as f:
            return json.load(f)
    return []

class VoteButton(Button):
    def __init__(self, server_id):
        super().__init__(
            label="Vote",
            style=discord.ButtonStyle.primary,
            custom_id=f"vote_{server_id}"
        )
        self.server_id = server_id

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        today = datetime.now().strftime("%Y-%m-%d")
        votes = load_votes()
        servers = load_servers()

        server = next((s for s in servers if s['name'].lower() == self.server_id.lower()), None)
        if not server or "message_id" not in server:
            await interaction.response.send_message("⚠️ Server didn't respond.", ephemeral=True)
            return

        server_name = server["name"]

        for data in votes.values():
            if today in data.get("by_day", {}) and user_id in data["by_day"][today]:
                await interaction.response.send_message("❗ You have already voted a server today.", ephemeral=True)
                return

        if server_name not in votes:
            votes[server_name] = {"total": 0, "by_day": {}}
        if today not in votes[server_name]["by_day"]:
            votes[server_name]["by_day"][today] = []

        votes[server_name]["by_day"][today].append(user_id)
        votes[server_name]["total"] += 1
        save_votes(votes)

                    # Απόδοση ρόλου
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("⚠️ Server didn't respond.", ephemeral=True)
            return

        voter_role = discord.utils.get(guild.roles, name="⚜️ Noblesse")
        member = guild.get_member(interaction.user.id)
        if member and voter_role:
            await member.add_roles(voter_role)

            # 🔍 Φόρτωση voters.json
            voters = load_voters()

            # Δημιουργία/ενημέρωση entry
            if user_id not in voters:
                voters[user_id] = {}

            # 🕒 Καταγραφή timestamp
            voters[user_id]["joined"] = datetime.now(timezone.utc).isoformat()

            # 🧹 Διαγραφή expired_dm αν υπάρχει
            expired_msg_id = voters[user_id].pop("expired_dm", None)
            if expired_msg_id:
                try:
                    dm = await member.create_dm()
                    msg = await dm.fetch_message(expired_msg_id)
                    await msg.delete()
                except:
                    pass

            # 💾 Προσπάθεια αποθήκευσης
            try:
                save_voters(voters)
            except Exception as e:
                print(f"[❌ ERROR] Failed to save {member.display_name} to voters.json: {e}")



        # Ενημέρωση του embed στο 📜server-list
        channel = discord.utils.get(guild.text_channels, name="📜︱server-list")
        if not channel:
            await interaction.response.send_message("❌ Channel 📜︱server-list not found.", ephemeral=True)
            return

        try:
            message = await channel.fetch_message(server["message_id"])
        except discord.NotFound:
            await interaction.response.send_message("⚠️ Server didn't respond.", ephemeral=True)
            return

        server["votes"] = votes[server_name]["total"]
        embed = generate_embed(server, context="serverlist")
        await message.edit(embed=embed, view=VoteView(server["name"]))

        # Ενημέρωση servers.json
        with open(SERVERS_FILE, "w") as f:
            json.dump(servers, f, indent=2)

        # ✅ Live update leaderboard embed
        try:
            message_id = server.get("leaderboard_message_id")
            if message_id:
                leaderboard_channel = discord.utils.get(guild.text_channels, name="🥇︱leaderboards")
                if leaderboard_channel:
                    try:
                        leaderboard_msg = await leaderboard_channel.fetch_message(message_id)
                        leaderboard_embed = generate_embed(server, context="leaderboard")
                        await leaderboard_msg.edit(embed=leaderboard_embed)
                    except discord.NotFound:
                        print(f"❌ Δεν βρέθηκε leaderboard μήνυμα για {server['name']}")
        except Exception as e:
            print(f"⚠️ Σφάλμα κατά το live refresh του leaderboard: {e}")

        # ✅ Τελικό μήνυμα στον χρήστη
        await interaction.response.send_message(
            "✅ Thank you for voting!\n\n"
            "You now have full access to:\n"
            "🥇 leaderboards\n"
            "⚜️ Heroes RPG\n"
            "📚 Guides\n"
            "📖 Lores\n"
            "💬 Community Chat\n\n"
            "See you in 24 hours!",
            ephemeral=True
        )



class VoteView(View):
    def __init__(self, server_id):
        super().__init__(timeout=None)
        self.add_item(VoteButton(server_id))


class UnsubscribeView(View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="Unsubscribe", style=discord.ButtonStyle.danger)
    async def unsubscribe(self, interaction: discord.Interaction, button: discord.ui.Button):
        unsubscribed = load_unsubscribed()
        unsubscribed[str(self.user_id)] = True
        save_unsubscribed(unsubscribed)
        await interaction.response.edit_message(content="You will no longer receive vote reminders in DMs.", view=None)
