from __future__ import annotations

from discord import Embed, Guild
from discord.utils import utcnow
from wavelink import Player, Playable


def get_stamp(seconds: int) -> str:
    """Returns a str with the minutes:seconds."""
    minutes = seconds // 60
    seconds %= 60
    min = f"{minutes}" if minutes >= 10 else f"0{minutes}"
    sec = f"{seconds}" if seconds >= 10 else f"0{seconds}"
    return f"{min}:{sec}"


def queue_builder(player: Player, page: int) -> Embed:
    """For Queue command."""
    pages = len(player.queue) // 10
    description = f"Now Playing- `{get_stamp(player.current.length // 1000)}` **[{player.current}]({player.current.uri})**"  # type: ignore

    for index, track in enumerate(player.queue[10 * (page - 1) : (page * 10) - 1]):
        description = description + (
            f"""
            {10 * (page - 1) + (index + 2)} - `[{get_stamp(track.length // 1000)}]` [{track}]({track.uri})"""
        )

    return Embed(
        title=f"Page {page}/{pages+1}",
        description=description,
        color=0x1E1F22,
    )


def play_builder(player: Player, track: Playable, author: str) -> Embed:
    """For Play Command when a song is added to queue"""
    embed = Embed(colour=0x00B0F4, timestamp=utcnow())
    embed.set_author(name="Added Track")

    embed.add_field(name="Track", value=f"[{track.title}]({track.uri})", inline=False)

    embed.add_field(
        name="Estimated time until played",
        value=f"`{get_stamp((player.current.length - player.position) // 1000)}`",  # type: ignore
        inline=True,
    )
    embed.add_field(
        name="Track Length",
        value=f"`{get_stamp(track.length // 1000)}`",
        inline=True,
    )
    embed.add_field(name="", value="", inline=False)
    value = "Next" if len(player.queue) == 1 else f"{len(player.queue)}"  # type: ignore
    embed.add_field(name="Position in upcoming", value=value, inline=True)
    embed.set_thumbnail(url=track.artwork)  # type: ignore

    embed.set_footer(
        text=f"Requested by {author}",
        icon_url="https://slate.dan.onl/slate.png",
    )

    return embed


def queue_message_builder(player: Player | None, guild: Guild | None = None) -> Embed:
    """For Setup Channel Queue."""
    url = "https://slate.dan.onl/slate.png"
    description = "Currently there are __0 Songs__ in the Queue."
    if guild:
        embed = Embed(
            title=f"Queue of __{guild.name}__",  # type: ignore
            color=0x1E1F22,
        )
        url = guild.icon or guild.banner  # type: ignore
    else:
        assert player is not None
        embed = Embed(
            title=f"Queue of __{player.home.guild.name}__",  # type: ignore
            color=0x1E1F22,
        )
        if player.playing:
            description = f"Now Playing- `{get_stamp(player.current.length // 1000)}` **[{player.current}]({player.current.uri})**"  # type: ignore
            for index, track in enumerate(player.queue[:9]):
                description = description + (
                    f"""
                {index+1} - `[{get_stamp(track.length // 1000)}]` [{track}]({track.uri})"""
                )
        if player.home:  # type: ignore
            url = player.home.guild.icon or player.home.guild.banner  # type: ignore
    embed.set_thumbnail(url=url)
    embed.description = description
    return embed


def playing_message_builder(player: Player, flag: bool = False) -> Embed:
    embed = Embed(
        title="Start Listening to Music, by connecting to a Voice Channel and sending either the SONG LINK or SONG NAME in this Channel!",
    )
    if flag:
        embed.add_field(
            name="Support me by joining my server!",
            value="https://discord.gg/5gzy2jHhyf",
        )
    elif player.current:
        embed.set_image(url=player.current.artwork)  # type: ignore
        embed.add_field(
            name="Now Playing",
            value=f"`{get_stamp(player.current.length // 1000)}` **[{player.current}]({player.current.uri})**",  # type: ignore
            inline=False,
        )
    else:
        embed.add_field(
            name="Support me by joining my server!",
            value="https://discord.gg/5gzy2jHhyf",
        )
    embed.set_footer(icon_url="https://slate.dan.onl/slate.png", text="Sangeet")
    return embed


def now_playing(player: Player) -> Embed:
    embed = Embed(
        title="Playing",
        description=f"[{player.current.title}]({player.current.uri})]",  # type: ignore
        colour=0x00B0F4,
        timestamp=utcnow(),
    )

    embed.set_author(name="Now Playing ♪", icon_url=player.current.artwork)  # type: ignore

    length = player.current.length // 1000  # type: ignore
    now = player.position // 1000

    postition = round((player.position * 15) / player.current.length)  # type: ignore
    x = "▬" * (postition - 1) + "🔘" + "▬" * (15 - postition)
    embed.add_field(name="Position", value=f"`{x}`", inline=True)
    embed.add_field(name="Position in queue", value="1", inline=True)
    embed.add_field(name="Position", value=get_stamp(now), inline=True)
    embed.add_field(name="Length", value=get_stamp(length), inline=True)
    return embed


def get_help(cmd: str | None = None) -> Embed:
    embed = Embed(
        title="Support Server.",
        url="https://discord.gg/5gzy2jHhyf",
        colour=0x00B0F4,
        timestamp=utcnow(),
    )
    embed.set_author(name="Help Command!", icon_url="https://slate.dan.onl/slate.png")

    embed.set_footer(text="Sangeet", icon_url="https://slate.dan.onl/slate.png")
    if cmd:
        embed.add_field(name=f"Help for {cmd}", value="Coming Soon!")
    else:
        des = """
**Setup**        -        Set up a channel for the bot.
**Join**         -        Joins your channel.
**Play**         -        Plays a song.
**Skip**         -        Skips the song playing.
**Stop**         -        Stops the song.
**Pause**        -        Pauses the player.
**Resume**       -        Resumes the player.
**Volume**       -        Changes the Volume of the bot.
**Shuffle**      -        Shuffles the queue of the bot.
**Loop**         -        Changes the loop mode.
**now**          -        Shows now playing.
        """
        embed.description = des

    return embed
