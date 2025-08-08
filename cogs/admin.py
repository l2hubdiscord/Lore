
import discord
from discord.ext import commands
import json
import os
from utils import generate_embed
from views import VoteView
import aiohttp
import time
from datetime import datetime, timezone, timedelta
from utils import save_voters, load_voters



SERVERS_FILE = "servers.json"
VOTES_FILE = "votes.json"

def load_servers():
    if os.path.exists(SERVERS_FILE):
        with open(SERVERS_FILE, "r") as f:
            return json.load(f)
    return []

def save_servers(servers):
    with open(SERVERS_FILE, "w") as f:
        json.dump(servers, f, indent=2)

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

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("[COGS] ✅ Loaded: cogs.admin")


    @commands.command()
    @commands.has_permissions(administrator=True)
    async def syncvoters(self, ctx):
        """Προσθέτει στο voters.json μόνο όσους έχουν τον ρόλο ⚜️ Noblesse και δεν υπάρχουν ήδη"""
        role = discord.utils.get(ctx.guild.roles, name="⚜️ Noblesse")
        if not role:
            await ctx.send("❌ Δεν βρέθηκε ο ρόλος ⚜️ Noblesse.")
            return

        voters = load_voters()
        now = datetime.now(timezone.utc).isoformat()

        added = 0
        for member in ctx.guild.members:
            if role in member.roles and str(member.id) not in voters:
                voters[str(member.id)] = { "joined": now }
                added += 1

        save_voters(voters)
        await ctx.send(f"✅ Προστέθηκαν {added} νέοι χρήστες στο voters.json.")
        print(f"[SYNCVOTERS] Προστέθηκαν {added} νέοι χρήστες με timestamp {now}")



    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx):
        print(f"🟡 [{time.time()}] Ξεκίνησε η εντολή !setup")

        channel = discord.utils.get(ctx.guild.text_channels, name="📜︱server-list")
        if not channel:
            await ctx.send("❌ Δεν βρέθηκε το κανάλι 📜︱server-list.")
            return

        print(f"🔵 [{time.time()}] Ξεκινάει το purge...")
        await channel.purge()
        print(f"🟢 [{time.time()}] Ολοκληρώθηκε το purge")

        print(f"📂 [{time.time()}] Ξεκινάει φόρτωμα servers...")
        servers = load_servers()
        votes = load_votes()
        print(f"✅ [{time.time()}] Ολοκληρώθηκε φόρτωμα servers")

        for server in servers:
            server["votes"] = votes.get(server["name"], {}).get("total", 0)
            embed = generate_embed(server, context="serverlist")
            message = await channel.send(embed=embed, view=VoteView(server["name"]))
            server["message_id"] = message.id

        save_servers(servers)
        print(f"🏁 [{time.time()}] Ολοκληρώθηκε η αποστολή embeds")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def addserver(self, ctx, name, chronicle, rates, website, discord_link, thumbnail, image=None):
        await ctx.message.delete()

        premium = image is not None
        votes = load_votes()
        servers = load_servers()

        new_server = {
            "name": name,
            "chronicle": chronicle,
            "rates": rates,
            "website": website,
            "discord": discord_link,
            "thumbnail": thumbnail,
            "premium": premium,
            "votes": 0
        }

        if premium:
            new_server["image"] = image

        embed = generate_embed(new_server, context="serverlist")
        channel = discord.utils.get(ctx.guild.text_channels, name="📜︱server-list")
        if not channel:
            await ctx.send("❌ Δεν βρέθηκε το κανάλι 📜︱server-list.")
            return

        message = await channel.send(embed=embed, view=VoteView(name))
        new_server["message_id"] = message.id

        servers.append(new_server)
        votes[name] = {"total": 0, "by_day": {}}
        save_votes(votes)
        save_servers(servers)

        # Προσθήκη View για μελλοντικό restart
        self.bot.add_view(VoteView(name))

    @commands.command(name="checkinvites")
    @commands.has_permissions(administrator=True)
    async def check_invites(self, ctx):
        with open("servers.json", "r", encoding="utf-8") as f:
            servers = json.load(f)

        invalid = []

        for server in servers:
            name = server["name"]
            invite = server.get("discord")
            if not invite:
                continue
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(invite) as resp:
                        if resp.status != 200:
                            invalid.append(f"❌ {name} – Invalid: {invite}")
            except Exception:
                invalid.append(f"❌ {name} – Invalid: {invite}")

        if not invalid:
            await ctx.send("✅ Όλα τα invite links είναι έγκυρα.", ephemeral=True)
            return

        # Σπάσιμο embed αν ξεπερνάμε το όριο
        MAX_CHARS = 3900
        current = ""
        embeds = []

        for line in invalid:
            if len(current) + len(line) > MAX_CHARS:
                embed = discord.Embed(
                    title="❌ Invalid Invite Links",
                    description=current,
                    color=discord.Color.red()
                )
                embeds.append(embed)
                current = ""
            current += line + "\n"

        if current:
            embed = discord.Embed(
                title="❌ Invalid Invite Links",
                description=current,
                color=discord.Color.red()
            )
            embeds.append(embed)

        for embed in embeds:
            await ctx.send(embed=embed, ephemeral=True)


    @commands.command()
    @commands.has_permissions(administrator=True)
    async def forceremoveexpired(self, ctx):
        """Force-remove Noblesse roles from users who joined over 24h ago (based on voters.json)"""
        await ctx.send("🔍 Checking for expired voters...")
        print("🧪 Running manual check for expired voters...")

        VOTERS_FILE = "voters.json"
        ROLE_ID = 1393227921182953644  
        GUILD_ID = 1392774389715701820

        try:
            with open(VOTERS_FILE, "r") as f:
                voters = json.load(f)
        except Exception as e:
            await ctx.send(f"❌ Failed to load voters.json: {e}")
            return

        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            await ctx.send("❌ Guild not found.")
            return

        role = guild.get_role(ROLE_ID)
        if not role:
            await ctx.send("❌ Role not found (check ROLE_ID).")
            return

        removed_count = 0
        for user_id, voter_info in voters.items():
            timestamp_str = voter_info.get("joined")
            if not timestamp_str:
                continue

            try:
                timestamp = datetime.fromisoformat(timestamp_str)
            except Exception as e:
                print(f"❌ Invalid timestamp for {user_id}: {e}")
                continue

            now = datetime.now(timezone.utc)
            diff = now - timestamp

            if diff >= timedelta(hours=24):
                try:
                    member = await guild.fetch_member(int(user_id))
                except discord.NotFound:
                    print(f"❌ User {user_id} not found.")
                    continue
                except Exception as e:
                    print(f"⚠️ Error fetching member {user_id}: {e}")
                    continue

                if role in member.roles:
                    try:
                        await member.remove_roles(role)
                        print(f"✅ Removed role from {member.display_name}")
                        removed_count += 1
                    except Exception as e:
                        print(f"❌ Failed to remove role: {e}")
                else:
                    print(f"ℹ️ {member.display_name} does not have the role.")

        await ctx.send(f"✅ Done. Removed role from {removed_count} users.")
    
    @commands.command()
    @commands.is_owner()
    async def reloadcogs(self, ctx):
        import os

        cogs_dir = "cogs"
        success, failed = [], []

        for filename in os.listdir(cogs_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                cog_name = filename[:-3]  # remove .py
                try:
                    await self.bot.reload_extension(f"cogs.{cog_name}")
                    success.append(cog_name)
                except Exception as e:
                    failed.append((cog_name, str(e)))

        msg = ""
        if success:
            msg += f"✅ Reloaded: {', '.join(success)}\n"
        if failed:
            msg += f"❌ Failed: " + ", ".join(f"{c} ({err})" for c, err in failed)

        await ctx.send(msg.strip())



async def setup(bot):
    await bot.add_cog(AdminCog(bot))
