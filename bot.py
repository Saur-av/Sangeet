from __future__ import annotations
import asyncio
from discord.ext import commands
from cogs.utils.config import (
    lavalink_port,
    lavalink_node,
    lavalink_password,
    timeout,
    c_appid,
)
from discord.ext.commands.context import Context
from discord.ext.commands.errors import CommandError
from cogs.utils.builders import queue_message_builder, playing_message_builder
from cogs.utils.ui_music import MusicButtons
import asyncpg
import discord
import wavelink
import logging
import random

description = "Simple Music Bot made by Sapi."

initial_extensions = ("cogs.general", "cogs.music")

log = logging.getLogger(__name__)


class Sangeet(commands.AutoShardedBot):
    user: discord.ClientUser
    pool: asyncpg.Pool

    def __init__(self):
        allowed_mentions = discord.AllowedMentions(
            roles=False, everyone=False, users=True
        )
        intents = discord.Intents(
            guilds=True,
            members=True,
            bans=True,
            emojis=True,
            voice_states=True,
            messages=True,
            reactions=True,
            message_content=True,
        )
        super().__init__(
            command_prefix=(",", f"<@!{c_appid}>", f"<@{c_appid}>"),
            description=description,
            help_command=None,
            chunk_guilds_at_startup=False,
            heartbeat_timeout=150.0,
            allowed_mentions=allowed_mentions,
            intents=intents,
        )
        self.spam_control = commands.CooldownMapping.from_cooldown(
            10, 12.0, commands.BucketType.user
        )

    async def setup_hook(self) -> None:
        async with self.pool.acquire() as conn:
            with open("sql/schema.sql", "r") as sql:
                await conn.execute(sql.read())
        self._setupdetails = {}  # serverid: [channelid, queueid, playingid]
        self._channels = [
            i["channelid"]
            for i in await self.pool.fetch("SELECT channelid FROM setupdetails")
        ]
        for i in await self.pool.fetch("SELECT * FROM setupdetails"):
            self._setupdetails[i["serverid"]] = [
                i["channelid"],
                i["queueid"],
                i["playingid"],
            ]
        await self.load_extension("jishaku")
        for extension in initial_extensions:
            try:
                await self.load_extension(extension)
            except Exception as e:
                print(f"Failed to load extension {extension}.")
                print(e)
        nodes = [
            wavelink.Node(
                uri=f"http://{lavalink_node}:{lavalink_port}"
                or "http://139.99.124.43:7784",
                password=lavalink_password or "PasswordIsZoldy",
                inactive_player_timeout=timeout,
            )
        ]
        self.add_view(MusicButtons())
        await wavelink.Pool.connect(nodes=nodes, client=self)

    async def on_wavelink_node_ready(
        self, payload: wavelink.NodeReadyEventPayload
    ) -> None:
        print(f"Wavelink Node connected: {payload.node!r} | Resumed: {payload.resumed}")

    async def on_wavelink_track_start(
        self, payload: wavelink.TrackStartEventPayload
    ) -> None:
        player: wavelink.Player | None = payload.player
        track: wavelink.Playable = payload.track
        delt = None
        assert player is not None
        if player.home.id in self._channels:  # type: ignore
            delt = 5
        embed: discord.Embed = discord.Embed(
            description=f"Started playing **[{track.title}]({track.uri})**",
            color=0x1E1F22,
        )
        await player.home.send(embed=embed, delete_after=delt)  # type: ignore

        if player.home.guild.id in self._setupdetails.keys():  # type: ignore
            channelid = self._setupdetails[player.home.guild.id][0]  # type: ignore
            try:
                setupchannel = player.home.guild.get_channel(channelid)  # type: ignore
                playing = setupchannel.get_partial_message(
                    self._setupdetails[player.home.guild.id][2]  # type: ignore
                )
                await playing.edit(embed=playing_message_builder(player))
            except Exception as e:
                print(e)

    async def on_wavelink_track_end(
        self, payload: wavelink.TrackEndEventPayload
    ) -> None:
        player: wavelink.Player | None = payload.player
        has_queue = False
        if player is None:
            return

        if player.queue:
            has_queue = True
            await player.play(player.queue.get())
            return
        if player.home.guild.id in self._setupdetails.keys():  # type: ignore
            channelid = self._setupdetails[player.home.guild.id][0]  # type: ignore
            try:
                setupchannel = player.home.guild.get_channel(channelid)  # type: ignore
                queue = setupchannel.get_partial_message(
                    self._setupdetails[player.home.guild.id][1]  # type: ignore
                )
                await queue.edit(embed=queue_message_builder(player))
                if not has_queue:
                    playing = setupchannel.get_partial_message(
                        self._setupdetails[player.home.guild.id][2]  # type: ignore
                    )
                    asyncio.sleep(2)
                    await playing.edit(embed=playing_message_builder(player, flag=True))
            except Exception as e:
                print(e)

    async def on_wavelink_track_exception(
        self, payload: wavelink.TrackExceptionEventPayload
    ) -> None:
        player: wavelink.Player | None = payload.player
        if player is None:
            return

        await player.home.send(  # type: ignore
            embed=discord.Embed(
                description=f"Please Check nodes [Call Sapi].",
                color=discord.Colour(0xFF0000),
            )
        )
        if payload.player.queue:
            await player.play(player.queue.get())
            return

    async def on_wavelink_inactive_player(self, player: wavelink.Player) -> None:
        await player.home.send(  # type: ignore
            embed=discord.Embed(
                description=f"The player has been inactive for `{player.inactive_timeout}` seconds. Goodbye!",
                color=discord.Colour(0xFF0000),
            ),
            delete_after=15,
        )
        await player.disconnect()
        player.cleanup()

    async def on_message(self, message: discord.Message) -> None:
        if message.author.id == self.user.id:
            return
        if message.channel.id in self._channels:
            await message.delete(delay=2)
            if message.content.startswith(tuple(self.command_prefix)):  # type: ignore
                await message.reply(
                    "You cannot use commands in this channel.", delete_after=5
                )
                return
            playcmd = self.get_command("play")
            assert playcmd is not None
            ctx = await self.get_context(message)
            await playcmd.invoke(ctx)
        await self.process_commands(message)

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id}).")  # type: ignore
        print("------")

    async def on_command_error(self, context: Context, exception: CommandError) -> None:
        if isinstance(exception, commands.CommandNotFound):
            return
        elif isinstance(exception, commands.CommandOnCooldown):
            await context.send(
                f"This command is on cooldown. Please try again after {exception.retry_after:.2f}s.",
                delete_after=5,
            )
        elif isinstance(exception, commands.MissingRequiredArgument):
            await context.send(
                f"You are missing a required argument: `{exception.param.name}`.",
                delete_after=5,
            )
        elif isinstance(exception, commands.BadArgument):
            await context.send(
                f"You passed in a bad argument: `{exception}`.", delete_after=5
            )
        elif isinstance(exception, commands.MissingPermissions):
            await context.send(
                f"You are missing the following permissions to run this command: `{exception.missing_permissions}`.",
                delete_after=5,
            )
        elif isinstance(exception, commands.BotMissingPermissions):
            await context.send(
                f"I am missing the following permissions to run this command: `{exception.missing_permissions}`.",
                delete_after=5,
            )
        elif isinstance(exception, commands.CommandInvokeError):
            await context.send(
                f"An error occurred while running the command: `{exception}`.",
                delete_after=5,
            )
        elif isinstance(exception, commands.CheckFailure):
            pass
        else:
            err = self.get_error_code()
            log.exception(err + " | " + str(exception))
            await context.send(
                f"An unknown error occurred while running the command: {err}.",
            )

    async def check(self, func): ...

    def get_error_code(self):
        err: str = "0x" + str(random.randint(100000, 999999))
        return err

    async def close(self) -> None:
        await self.pool.close()
        await super().close()
