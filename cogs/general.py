from __future__ import annotations
import discord
import asyncio
from discord.ext import commands
from cogs.utils.context import Context
from cogs.utils.builders import get_help
from typing import Union
from bot import Sangeet


class General(commands.Cog):
    def __init__(self, bot):
        self.bot: Sangeet = bot

    @commands.hybrid_command(name="ping", description="Get the bot's API latency.")
    async def ping(self, ctx: Context) -> None:
        """Get the bot's current API latency."""
        await ctx.send(
            embed=discord.Embed(
                title="Pong!",
                description=f"{self.bot.latency * 1000:.2f} ms!",
                color=discord.Color.green(),
            ),
        )

    @commands.hybrid_command(name="invite", description="Get the bot's invite link.")
    async def invite(self, ctx: Context) -> None:
        """Get the bot's invite link."""
        await ctx.send(
            embed=discord.Embed(
                title="Invite me in your server!",
                description=f"[Click Here.](https://discord.com/api/oauth2/authorize?client_id={ctx.me.id}&permissions=8&scope=bot)",
            )
        )

    @commands.command(name="support", description="Get the bot's support server link.")
    async def support(self, ctx: Context) -> None:
        """Get the bot's support server link."""
        await ctx.send(
            embed=discord.Embed(
                title="Our server!",
                description="[Click Here.](https://discord.gg/5gzy2jHhyf) \n\nShow us some love, join the support server!",
                color=discord.Color.green(),
            )
        )

    @commands.command(name="sync")
    @commands.guild_only()
    @commands.is_owner()
    async def sync(
        self,
        ctx: Context,
        guilds: commands.Greedy[discord.Object],
        spec: str | None = None,
    ) -> None:
        if not guilds:
            if spec == "~":
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "*":
                ctx.bot.tree.copy_global_to(guild=ctx.guild)  # type: ignore
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "^":
                ctx.bot.tree.clear_commands(guild=ctx.guild)
                await ctx.bot.tree.sync(guild=ctx.guild)
                synced = []
            else:
                synced = await ctx.bot.tree.sync()

            await ctx.send(
                f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
            )
            return

        ret = 0
        for guild in guilds:
            try:
                await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                ret += 1

        await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")

    @commands.is_owner()
    @commands.command(name="owner")
    async def owner(self, ctx: Context, *, message) -> None:
        for guilds in self.bot.guilds:
            try:
                assert guilds.owner is not None
                await guilds.owner.send(message)
                await asyncio.sleep(1)
            except Exception:
                pass

    @commands.hybrid_command(name="avatar", description="Gets the avatar of a user!")
    async def slash_avatarcmd(
        self,
        ctx: Context,
        user: Union[discord.Member, None, discord.User] = None,
        hidden: bool = False,
    ):
        """Gets the avatar of a user!"""
        if user is None:
            user = ctx.author

        embed = discord.Embed(
            title="Avatar link", url=user.display_avatar.url, colour=0x00B0F4
        )

        embed.set_author(
            name=user.name + user.discriminator, icon_url=user.display_avatar.url
        )

        embed.set_image(url=user.display_avatar.url)

        embed.set_footer(
            text=f"Requested by {ctx.author.name}",
            icon_url="https://slate.dan.onl/slate.png",
        )
        await ctx.send(embed=embed, ephemeral=hidden)

    @commands.hybrid_command(name="help", description="Help Command!")
    async def helpcmd(self, ctx: Context):
        await ctx.send(embed=get_help())

    @commands.is_owner()
    @commands.command(name="guilds")
    async def guildscmd(self, ctx: Context):
        des = ""
        for guild in self.bot.guilds:
            try:
                testing = await guild.invites()
                invite = testing[0]
            except:
                invite = None
            if invite is None:
                des += f"{guild.name} - {guild.id}\n"
            else:
                des += f"{guild.name} - {guild.id} - {invite.url}\n"
        await ctx.send(
            embed=discord.Embed(
                title="Guilds",
                description=des,
                color=discord.Color.green(),
            )
        )

    @commands.is_owner()
    @commands.command(name="leaveserver")
    async def leavecmd(self, ctx: Context, id: int):
        guild = self.bot.get_guild(id)
        if guild is None:
            await ctx.send("Guild not found")
            return
        await guild.leave()
        await ctx.send(f"Left server {guild.name}")


async def setup(bot: Sangeet):
    await bot.add_cog(General(bot))
