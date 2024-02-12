from discord.interactions import Interaction
from typing import cast
from cogs.utils.builders import queue_message_builder, playing_message_builder
import discord
import wavelink
import asyncio


class MusicButtons(discord.ui.View):
    """This class is used to create a persistent view for the music commands."""

    def __init__(self):
        super().__init__(timeout=None)

    async def interaction_check(self, interaction: Interaction) -> bool:  # type: ignore
        """This check looks for following things:
        - If the user is in a voice channel
        - If the bot is in a voice channel
        - If the bot is in the same voice channel as the user
        - If the bot has something in queue"""

        if interaction.user.voice is None:  # type: ignore
            await interaction.response.send_message(
                "You are not connected to a voice channel!",
                ephemeral=True,
            )
            return False

        if interaction.guild.me.voice is None:  # type: ignore
            await interaction.response.send_message(
                "I am not connected to a voice channel!",
                ephemeral=True,
            )
            return False

        if (
            interaction.guild.me.voice.channel.id  # type: ignore
            != interaction.user.voice.channel.id  # type: ignore
        ):
            await interaction.response.send_message(
                "I am already connected to another voice channel!",
                ephemeral=True,
            )
            return False

        player: wavelink.Player
        player = cast(wavelink.Player, interaction.guild.voice_client)  # type: ignore

        if not player:
            await interaction.response.send_message(
                "I am not connected to any voice channel!",
                ephemeral=True,
                delete_after=5,
            )
            return False

        if player.playing is not True:
            await interaction.response.send_message(
                "The Queue is empty!",
                ephemeral=True,
            )
            return False

        return True

    @discord.ui.button(
        label="Skip",
        style=discord.ButtonStyle.blurple,
        custom_id="persistent_view:skip",
        emoji="\U000023ed\U0000fe0f",
        row=1,
    )
    async def skip_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        player: wavelink.Player
        player = cast(wavelink.Player, interaction.guild.voice_client)  # type: ignore
        if not player.current:
            await interaction.response.send_message(
                ephemeral=True,
                embed=discord.Embed(
                    description="There is nothing in the queue!",
                    color=discord.Color(int("FF0000", 16)),
                ),
            )
            return
        des, color = f"**[{player.current.title}]({player.current.uri})** has been skipped", "00FF00"  # type: ignore
        await player.skip()
        await interaction.response.send_message(
            ephemeral=True,
            delete_after=5,
            embed=discord.Embed(description=des, color=discord.Color(int(color, 16))),
        )

    @discord.ui.button(
        label="Stop",
        style=discord.ButtonStyle.red,
        custom_id="persistent_view:stop",
        emoji="\U0001f3e0",
        row=1,
    )
    async def stop_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        player: wavelink.Player
        player = cast(wavelink.Player, interaction.guild.voice_client)  # type: ignore

        await player.disconnect()
        player.cleanup()

        await interaction.response.send_message(
            ephemeral=True,
            delete_after=5,
            embed=discord.Embed(
                description="Disconected! :wave:",
                color=discord.Color(int("A53F4E", 16)),
            ),
        )

        player: wavelink.Player = cast(wavelink.Player, interaction.guild.voice_client)  # type: ignore
        queue_embed = queue_message_builder(player=None, guild=interaction.guild)

        playing_embed = playing_message_builder(player, flag=True)

        bot = interaction.client

        assert interaction.guild
        if interaction.guild.id in bot._setupdetails.keys():  # type: ignore
            channelid = bot._setupdetails[interaction.guild.id][0]  # type: ignore
            setupchannel = interaction.guild.get_channel(channelid)
            queue = setupchannel.get_partial_message(  # type: ignore
                bot._setupdetails[interaction.guild.id][1]  # type: ignore
            )
            await queue.edit(embed=queue_embed)
            await asyncio.sleep(1)
            nowp = setupchannel.get_partial_message(  # type: ignore
                bot._setupdetails[interaction.guild.id][2]  # type: ignore
            )
            await nowp.edit(embed=playing_embed)

    @discord.ui.button(
        label="Pause",
        style=discord.ButtonStyle.grey,
        custom_id="persistent_view:toogle",
        emoji="\U000023f8",
        row=1,
    )
    async def pause_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        player: wavelink.Player
        player = cast(wavelink.Player, interaction.guild.voice_client)  # type: ignore

        if player is None:
            await interaction.response.send_message(
                ephemeral=True,
                embed=discord.Embed(
                    description="I am not connected to any voice channel!",
                    color=discord.Color(int("FF0000", 16)),
                ),
            )
            return

        await player.pause(not player.paused)

        if player.paused:
            button.label = "Resume"
            button.style = discord.ButtonStyle.green
            button.emoji = "\U000025b6\U0000fe0f"  # type: ignore
            description = "Track has been paused :play_pause:"
        else:
            button.label = "Pause"
            button.style = discord.ButtonStyle.grey
            button.emoji = "\U000023f8"
            description = "Track has been resumed :play_pause:"

        await interaction.response.edit_message(view=self)

        await interaction.followup.send(
            embed=discord.Embed(
                description=description, color=discord.Color(int("00ff00", 16))
            ),
            ephemeral=True,
        )

    @discord.ui.button(
        label="Shuffle",
        style=discord.ButtonStyle.blurple,
        custom_id="persistent_view:shuffle",
        emoji="\U0001f500",
        row=1,
    )
    async def shuffle_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        player: wavelink.Player
        player = cast(wavelink.Player, interaction.guild.voice_client)  # type: ignore

        player.queue.shuffle()

        await interaction.response.send_message(
            ephemeral=True,
            delete_after=5,
            embed=discord.Embed(
                description="Queue has been shuffled :twisted_rightwards_arrows:",
                color=discord.Color(int("00FF00", 16)),
            ),
        )

    @discord.ui.button(
        label="Song",
        style=discord.ButtonStyle.green,
        custom_id="persistent_view:song",
        emoji="\U0001f502",
        row=2,
    )
    async def song_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        player: wavelink.Player
        player = cast(wavelink.Player, interaction.guild.voice_client)  # type: ignore
        player.queue.mode = wavelink.QueueMode.loop

        await interaction.response.send_message(
            ephemeral=True,
            delete_after=5,
            embed=discord.Embed(
                description="I will now repeat the current track :repeat_one:",
                color=discord.Color(int("00FF00", 16)),
            ),
        )

    @discord.ui.button(
        label="Queue",
        style=discord.ButtonStyle.green,
        custom_id="persistent_view:queue",
        emoji="\U0001f501",
        row=2,
    )
    async def queue_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        player: wavelink.Player
        player = cast(wavelink.Player, interaction.guild.voice_client)  # type: ignore
        player.queue.mode = wavelink.QueueMode.loop_all
        await interaction.response.send_message(
            ephemeral=True,
            delete_after=5,
            embed=discord.Embed(
                description="I will now repeat the entire queue :repeat:",
                color=discord.Color(int("00FF00", 16)),
            ),
        )

    @discord.ui.button(
        label="Autoplay",
        style=discord.ButtonStyle.grey,
        custom_id="persistent_view:autoplay",
        emoji=discord.PartialEmoji(name="Autoplay", id=1200515733327708222),
        row=2,
    )
    async def autoplay_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        player: wavelink.Player
        player = cast(wavelink.Player, interaction.guild.voice_client)  # type: ignore

        if player.autoplay is wavelink.AutoPlayMode.enabled:
            player.autoplay = wavelink.AutoPlayMode.disabled
            button.style = discord.ButtonStyle.grey
            description = "Autoplay is now disabled :no_entry:"
        else:
            player.autoplay = wavelink.AutoPlayMode.enabled
            button.style = discord.ButtonStyle.green
            description = "Autoplay is now enabled :white_check_mark:"

        await interaction.response.edit_message(view=self)

        await interaction.followup.send(
            embed=discord.Embed(
                description=description, color=discord.Color(int("00ff00", 16))
            ),
            ephemeral=True,
        )
