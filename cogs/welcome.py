import discord
from discord.ext import commands
import asyncio

WELCOME_CHANNEL_ID = 1392774390244053013  # ID του #welcome
SERVER_LIST_CHANNEL_ID = 1393228933369036840  # ID του #server-list

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("[COGS] ✅ Loaded: cogs.welcome")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await self.send_welcome_message(member)

    async def schedule_deletion(self, message: discord.Message, days: int = 7):
        await asyncio.sleep(days * 86400)
        try:
            await message.delete()
        except discord.NotFound:
            pass

    async def send_welcome_message(self, member: discord.Member):
        guild = member.guild
        welcome_channel = guild.get_channel(WELCOME_CHANNEL_ID)
        serverlist_channel = guild.get_channel(SERVER_LIST_CHANNEL_ID)

        assert isinstance(welcome_channel, discord.TextChannel)
        assert isinstance(serverlist_channel, discord.TextChannel)


        await welcome_channel.send(f"Everyone Welcome {member.mention}!")

        embed = discord.Embed(
            title="🔒 Unlock L||ore Server",
            description=(
                f"To gain access to all channels, go to the channel {serverlist_channel.mention}\n"
                "and click ✅ Vote on a server. You'll unlock full access for 24 hours!"
            ),
            color=discord.Color.red()
        )
        embed.set_footer(text="This message will be deleted in 7 days.")

        
        msg = await welcome_channel.send(embed=embed)
        await self.schedule_deletion(msg, days=7)


async def setup(bot):
    await bot.add_cog(Welcome(bot))
