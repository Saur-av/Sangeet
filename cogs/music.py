from __future__ import annotations
import discord
import wavelink
import asyncio
from traceback import print_exc
from bot import Sangeet
from discord import app_commands
from cogs.utils.context import Context
from discord.ext import commands
from cogs.utils.ui_music import MusicButtons
from cogs.utils.context import Context, GuildContext
from cogs.utils.builders import (
    queue_builder,
    play_builder,
    queue_message_builder,
    now_playing,
    playing_message_builder,
)
from typing import cast


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot: Sangeet = bot

    async def cog_check(self, ctx: GuildContext) -> bool:
        await ctx.message.delete(delay=3)
        command_name = ctx.command.name

        if command_name == "setup":
            return True

        if ctx.author.voice is None:
            await ctx.send(
                embed=discord.Embed(
                    description="You are not in a Voice Channel.", color=0xFF0000
                ),
                delete_after=7,
            )
            return False
        if command_name == "join":
            if ctx.guild.me.voice is None or len(ctx.guild.me.voice.channel.members) == 1:  # type: ignore
                return True
            else:
                await ctx.send(
                    embed=discord.Embed(
                        description="I am already in a Voice Channel.", color=0xFF0000
                    ),
                    delete_after=7,
                )
                return False

        if ctx.guild.me.voice and ctx.author.voice.channel.id != ctx.guild.me.voice.channel.id:  # type: ignore
            await ctx.send(
                embed=discord.Embed(
                    description="I am already connected to another voice channel.",
                    color=0xFF0000,
                ),
                delete_after=7,
            )
            return False

        if command_name in ("play", "stop"):
            return True
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player:
            await ctx.send(
                embed=discord.Embed(
                    description="I am not connected to a voice channel.", color=0xFF0000
                ),
                delete_after=7,
            )
            return False

        if player.playing is not True:
            await ctx.send(
                embed=discord.Embed(description="Queue is empty.", color=0xFF0000),
                delete_after=7,
            )
            return False
        return True

    @commands.hybrid_command(name="setup")
    @app_commands.describe(channel="The channel to setup the bot in.")
    @commands.has_permissions(manage_channels=True)
    @commands.guild_only()
    async def setupcmd(
        self,
        ctx: GuildContext,
        channel: discord.TextChannel | None = None,
    ) -> None:
        """Setup the bot in the server."""
        color = 0xFF0000
        delt = 5
        if ctx.author.guild_permissions.manage_channels is False:
            des = "You need to be an have `manage_channels` to use this command."
            await ctx.send(
                embed=discord.Embed(description=des, color=color), delete_after=delt
            )
        if channel is None:
            des = "Please mention a channel."
            await ctx.send(
                embed=discord.Embed(description=des, color=color), delete_after=delt
            )
        assert channel is not None
        mbed = discord.Embed(
            title=f":page_with_curl: Queue of {ctx.guild.name}",
            description=f"Currently there are __0 Songs__ in the Queue.",
        )
        mbed.set_thumbnail(url=ctx.guild.banner)
        queue = await channel.send(embed=mbed)

        assert self.bot.user, "For Type Checking"
        mbed1 = discord.Embed(
            title="Start Listening to Music, by connecting to a Voice Channel and sending either the **SONG LINK** or **SONG NAME** in this Channel!",
            description=f"I support Youtube!",
        )
        mbed1.set_footer(text=self.bot.user.name, icon_url=self.bot.user.display_avatar)
        setup = await channel.send(embed=mbed1, view=MusicButtons())

        if ctx.guild.id in self.bot._setupdetails.keys():  # type: ignore
            await self.bot.pool.execute(
                "DELETE FROM setupdetails WHERE serverid = $1", ctx.guild.id
            )  # type: ignore
            self.bot._channels.remove(self.bot._setupdetails[ctx.guild.id][0])  # type: ignore
        self.bot._setupdetails[ctx.guild.id] = [channel.id, queue.id, setup.id]  # type: ignore
        self.bot._channels.append(channel.id)  # type: ignore
        await self.bot.pool.execute(
            "INSERT INTO setupdetails(serverid, channelid, queueid, playingid) VALUES($1, $2, $3, $4)",
            ctx.guild.id,
            channel.id,
            queue.id,
            setup.id,
        )
        des, color = (
            f"{channel.mention} has been configured! [If there is nothing setup a new Channel with 0 messages]",
            0x00FF00,
        )
        await ctx.send(embed=discord.Embed(description=des, color=color), delete_after=delt)  # type: ignore

    @commands.hybrid_command(
        name="join", describe="Joins the Voice Channel.", aliases=("j",)
    )
    async def joincmd(self, ctx: GuildContext) -> None:
        """Joins the Voice Channel."""
        await ctx.author.voice.channel.connect(cls=wavelink.Player, self_deaf=True)  # type: ignore
        des, color, delt = "Joined the Voice Channel!", 0x00FF00, 5
        await ctx.send(embed=discord.Embed(description=des, color=color), delete_after=delt)  # type: ignore

    @commands.hybrid_command(
        name="stop",
        describe="Disconnects from the Channel.",
        aliases=(
            "dc",
            "leave",
        ),
    )
    async def stopcmd(self, ctx: GuildContext) -> None:
        """Disconnects from the Channel."""
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        await ctx.voice_client.disconnect(force=True)  # type: ignore
        player.cleanup()
        await ctx.send(
            embed=discord.Embed(
                description="Disconnected from the Voice Channel.", color=0x00FF00
            ),
            delete_after=5,
        )

        if ctx.guild.id in self.bot._setupdetails.keys():
            queue_embed = queue_message_builder(player=None, guild=ctx.guild)
            playing_embed = playing_message_builder(player, flag=True)

            channelid = self.bot._setupdetails[ctx.guild.id][0]
            setupchannel = ctx.guild.get_channel(channelid)
            if channelid and setupchannel:
                queue = setupchannel.get_partial_message(  # type: ignore
                    self.bot._setupdetails[ctx.guild.id][1]
                )
                nowp = setupchannel.get_partial_message(  # type: ignore
                    self.bot._setupdetails[ctx.guild.id][2]
                )
                await nowp.edit(embed=playing_embed)
                await asyncio.sleep(0.75)
                await queue.edit(embed=queue_embed)

    @commands.hybrid_command(
        name="pause", describe="Pauses the player.", aliases=["toogle", "pau"]
    )
    async def pausecmd(self, ctx: GuildContext) -> None:
        """Pauses the player."""
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        await player.pause(not player.pause)
        await ctx.send(
            embed=discord.Embed(
                description=(
                    "Track has been **resumed** :play_pause:"
                    if player.playing
                    else "Track has been **paused** :play_pause:"
                ),
                color=0x00FF00,
            )
        )

    @commands.hybrid_command(
        name="resume", describe="Resumes the player.", aliases=["res"]
    )
    async def resumecmd(self, ctx: GuildContext) -> None:
        """Pauses the player."""
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        await player.pause(not player.pause)
        await ctx.send(
            embed=discord.Embed(
                description=(
                    "Track has been **resumed** :play_pause:"
                    if player.playing
                    else "Track has been **paused** :play_pause:"
                ),
                color=0x00FF00,
            )
        )

    @commands.hybrid_command(
        name="skip", describe="Skips the current song.", aliases=["s"]
    )
    async def skipcmd(self, ctx: GuildContext) -> None:
        """Skips the current song."""
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        await ctx.send(
            embed=discord.Embed(
                description=f"**[{player.current}]({player.current.uri})** has been skipped",  # type: ignore
                color=0x00FF00,
            )
        )
        await player.skip()
        if ctx.guild.id in self.bot._setupdetails.keys():
            queue_embed = queue_message_builder(player)

            channelid = self.bot._setupdetails[ctx.guild.id][0]
            setupchannel = ctx.guild.get_channel(channelid)
            if channelid and setupchannel:
                queue = setupchannel.get_partial_message(  # type: ignore
                    self.bot._setupdetails[ctx.guild.id][1]
                )
                await queue.edit(embed=queue_embed)

    @commands.hybrid_command(
        name="volume", describe="Change volume of the player.", aliases=["vol"]
    )
    @app_commands.describe(volume="The volume to set.")
    async def volumnecmd(self, ctx: GuildContext, volume: int = 100) -> None:
        """Change volume of the player."""
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if volume > 150:
            volume = 150
        await player.set_volume(volume)
        await ctx.send(
            embed=discord.Embed(
                description=f"Changed the volume to {volume}%", color=0x00FF00
            )
        )

    @commands.hybrid_command(
        name="shuffle", describe="Shuffles the Queue.", aliases=["sf"]
    )
    async def shufflecmd(self, ctx: GuildContext) -> None:
        """Shuffles the Queue."""
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        player.queue.shuffle()  # type: ignore
        await ctx.send(
            embed=discord.Embed(
                description="Queue has been shuffled :twisted_rightwards_arrows:",
                color=0x00FF00,
            )
        )
        if ctx.guild.id in self.bot._setupdetails.keys():
            queue_embed = queue_message_builder(player)

            channelid = self.bot._setupdetails[ctx.guild.id][0]
            setupchannel = ctx.guild.get_channel(channelid)
            if channelid and setupchannel:
                queue = setupchannel.get_partial_message(  # type: ignore
                    self.bot._setupdetails[ctx.guild.id][1]
                )
                await queue.edit(embed=queue_embed)

    @commands.hybrid_command(name="loop")
    @app_commands.choices(
        mode=[
            app_commands.Choice(name="off", value="normal"),
            app_commands.Choice(name="queue", value="loop_all"),
            app_commands.Choice(name="song", value="loop"),
        ]
    )
    async def loopcmd(self, ctx: GuildContext, mode: app_commands.Choice[str]) -> None:
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if mode.value == "normal":
            player.queue.mode = wavelink.QueueMode.normal
            description = "I will no longer repeat the queue. :x:"
        elif mode.value == "loop_all":
            player.queue.mode = wavelink.QueueMode.loop_all
            description = "I will now repeat the queue :repeat:"
        elif mode.value == "loop":
            player.queue.mode = wavelink.QueueMode.loop
            description = "I will now repeat the current track :repeat_one:"
        else:
            description = "Invalid mode! [off,queue,song]"
        await ctx.send(embed=discord.Embed(description=description, color=0x00FF00))

    @commands.hybrid_command(
        name="play", describe="Plays a song through the bot.", aliases=["p"]
    )
    @app_commands.describe(query="The [name | link] of song to play.")
    async def playcmd(self, ctx: GuildContext, *, query: str) -> None:
        player: wavelink.Player = cast(wavelink.Player, ctx.guild.voice_client)  # type: ignore
        delt = None
        if ctx.guild.me.voice is None:  # type: ignore
            player = await ctx.author.voice.channel.connect(cls=wavelink.Player, self_deaf=True)  # type: ignore

        tracks: wavelink.Search = await wavelink.Playable.search(query)

        if not hasattr(player, "home"):  # type: ignore
            player.home = ctx.channel  # type: ignore
        if ctx.channel.id in self.bot._channels:
            delt = 5
        if not tracks:
            await ctx.send(
                embed=discord.Embed(
                    description="No Results.:no_entry:", color=0x00FF00
                ),
                delete_after=delt,  # type: ignore
            )
            return
        if isinstance(tracks, wavelink.Playlist):
            # tracks is a playlist...
            added: int = player.queue.put(tracks)  # type: ignore
            await ctx.send(
                embed=discord.Embed(
                    description=f"Added the playlist [{tracks.name}]({tracks.url}) ({added} songs) to the queue.",
                    color=0x1E1F22,
                ),
                delete_after=delt,  # type: ignore
            )
        else:
            track: wavelink.Playable = tracks[0]
            player.queue.put(track)  # type: ignore
            if player.playing:
                await ctx.send(embed=play_builder(player, track, ctx.author.name), delete_after=delt)  # type: ignore
        if player.playing is not True:  # type: ignore
            await player.play(player.queue.get(), volume=100)  # type: ignore

        if ctx.guild.id in self.bot._setupdetails.keys():
            queue_embed = queue_message_builder(player)
            channelid = self.bot._setupdetails[ctx.guild.id][0]
            setupchannel = ctx.guild.get_channel(channelid)
            if setupchannel:
                queue = setupchannel.get_partial_message(  # type: ignore
                    self.bot._setupdetails[ctx.guild.id][1]
                )
                await queue.edit(embed=queue_embed)

    @commands.hybrid_command(
        name="queue",
        describe="Displays the songs in it's Queue.",
        aliases=(
            "q",
            "list",
        ),
    )
    @app_commands.describe(page="The page number.")
    async def queue_cmd(self, ctx: GuildContext, page: int = 1) -> None:
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        await ctx.send(embed=queue_builder(player, page))

    @commands.hybrid_command(name="now", describe="Displays the current song.")
    async def nowcmd(self, ctx: GuildContext) -> None:
        player: wavelink.Player = cast(wavelink.Player, ctx.guild.voice_client)  # type: ignore
        await ctx.send(embed=now_playing(player))

async def setup(bot: Sangeet):
    await bot.add_cog(Music(bot))
