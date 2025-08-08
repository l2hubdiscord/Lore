import discord
from discord.ext import commands, tasks
from datetime import datetime, timezone, timedelta
import json
import os
import asyncio
from views import VoteView
from views import UnsubscribeView
from utils import generate_embed

LAST_RESET_FILE = "last_reset.json"
VOTES_FILE = "votes.json"
SERVERS_FILE = "servers.json"
ROLE_NAME = "⚜️ Noblesse"

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

def load_last_reset():
    if os.path.exists(LAST_RESET_FILE):
        with open(LAST_RESET_FILE, "r") as f:
            return json.load(f)
    return {"last_reset_date": None}

def save_last_reset(date_str):
    with open(LAST_RESET_FILE, "w") as f:
        json.dump({"last_reset_date": date_str}, f)

class VoteCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voters = {}

        if os.path.exists("voters.json"):
            with open("voters.json", "r") as f:
                self.voters = json.load(f)

        self.reset_votes_monthly.start()
        print("✅ Started reset_votes loop")




    @commands.command()
    @commands.has_permissions(administrator=True)
    async def resetvotes(self, ctx):
        votes = load_votes()
        for server_name in votes:
            votes[server_name] = {"total": 0, "by_day": {}}
        save_votes(votes)
        await ctx.send("✅ All votes have been reset manually.")
        print("🔁 Manual vote reset executed via command.")

    @tasks.loop(hours=24)
    async def reset_votes_monthly(self):
        await self.bot.wait_until_ready()
        now = datetime.datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        last_reset = load_last_reset()

        if now.day != 1 or last_reset["last_reset_date"] == today_str:
            return

        votes = load_votes()
        for server_name in votes:
            votes[server_name]["total"] = 0
            votes[server_name]["by_day"] = {}
        save_votes(votes)
        save_last_reset(today_str)
        print("🗓️ Votes reset for all servers (monthly).")

    @commands.Cog.listener()
    @commands.Cog.listener()
    async def on_ready(self):
        print("[COGS] ✅ Loaded: cogs.vote")
        if not hasattr(self.bot, "noblesse_task_started"):
            self.bot.noblesse_task_started = True
            asyncio.create_task(self._check_noblesse_expiry_loop())
            print("[LOOPS] ✅ Started noblesse expiry check loop.")


    @commands.command()
    @commands.is_owner()
    async def reloadvoters(self, ctx):
        try:
            with open("voters.json", "r") as f:
                self.voters = json.load(f)
            await ctx.send("✅ Voters reloaded from file.")
        except Exception as e:
            await ctx.send(f"❌ Error reloading voters: {e}")



    async def _check_noblesse_expiry_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                with open("voters.json", "r") as f:
                    self.voters = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                self.voters = {}

            guild = self.bot.get_guild(1392774389715701820)
            if guild is None:
                await asyncio.sleep(60)
                continue

            role = discord.utils.get(guild.roles, name=ROLE_NAME)
            if role is None:
                await asyncio.sleep(60)
                continue

            now = datetime.now(timezone.utc)
            to_remove = []
            now = datetime.now(timezone.utc)

            for user_id, data in self.voters.items():
                try:
                    timestamp = datetime.fromisoformat(data["joined"])
                except:
                    continue

                if now - timestamp > timedelta(hours=24):
                    member = guild.get_member(int(user_id))
                    if member and role in member.roles:
                        await member.remove_roles(role)
                        print(f"🧹 Removed {ROLE_NAME} from {member.display_name}")
                        to_remove.append(user_id)

                        # ✉️ Attempt DM unless user unsubscribed
                        try:
                            with open("unsubscribe_list.json", "r") as f:
                                unsubscribed = json.load(f)
                        except:
                            unsubscribed = {}

                        if str(member.id) not in unsubscribed:
                            try:
                                serverlist_channel = self.bot.get_channel(1393228933369036840)
                                dm = await member.create_dm()
                                embed = discord.Embed(
                                    title="🔒 Access Expired",
                                    description=(
                                        f"Your 24-hour access to the L||ore server has expired.\n\n"
                                        f"To regain access, go to {serverlist_channel.mention} and click ✅ **Vote** on any server.\n"
                                        f"You'll instantly unlock all features again!"
                                    ),
                                    color=discord.Color.red()
                                )
                                view = UnsubscribeView(member.id)
                                message = await dm.send(embed=embed, view=view)

                                self.voters[user_id]["expired_dm"] = message.id
                                with open("voters.json", "w") as f:
                                    json.dump(self.voters, f, indent=4)

                            except Exception as e:
                                print(f"[DM ERROR] {member.id}: {e}")


            for uid in to_remove:
                expired_dm = self.voters[uid].get("expired_dm")
                if expired_dm:
                    self.voters[uid] = {"expired_dm": expired_dm}
                else:
                    del self.voters[uid]


            if to_remove:
                with open("voters.json", "w") as f:
                    json.dump(self.voters, f, indent=4)

            await asyncio.sleep(60)


async def setup(bot):
    await bot.add_cog(VoteCog(bot))
    