# type : ignore
from __future__ import annotations
import discord
from discord.ext import commands
from typing import Any, Union

from bot import Sangeet
from asyncpg.pool import Pool


class Context(commands.Context):
    channel: Union[
        discord.VoiceChannel, discord.TextChannel, discord.Thread, discord.DMChannel
    ]
    prefix: str
    command: commands.Command[Any, ..., Any]
    bot: Sangeet
    author: discord.Member

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pool: Pool = self.bot.pool


class GuildContext(Context):
    author: discord.Member
    guild: discord.Guild
    channel: Union[discord.VoiceChannel, discord.TextChannel, discord.Thread]
    me: discord.Member
    prefix: str
