import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import json
import os

# =========================================================
# CONFIG
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

# Role that is allowed to use /rewards
REWARDS_ADMIN_ROLE_ID = 1547436901428891660

# Reward roles
FIVE_INVITE_ROLE = 1551687592678793246
TEN_INVITE_ROLE = 1551687732953088091
FIFTEEN_INVITE_ROLE = 1551688333443465347
INVITE_LOG_CHANNEL_ID = 1542342156428255242

# =========================================================
# BOT SETUP
# =========================================================

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.invites = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# =========================================================
# INVITE DATA
# =========================================================

invite_data = {}
invite_cache = {}


# =========================================================
# LOAD / SAVE DATA
# =========================================================

def load_data():
    global invite_data

    try:
        with open("invite_data.json", "r") as file:
            invite_data = json.load(file)

        print("Invite data loaded.")

    except FileNotFoundError:
        invite_data = {}


def save_data():
    with open("invite_data.json", "w") as file:
        json.dump(invite_data, file, indent=4)


# =========================================================
# GET USER INVITES
# =========================================================

def get_invites(user_id):
    return invite_data.get(str(user_id), 0)


# =========================================================
# ADD INVITE
# =========================================================

async def add_invite(guild, user_id, invited_member=None):

    user_id = str(user_id)

    if user_id not in invite_data:
        invite_data[user_id] = 0

    # Add the invite
    invite_data[user_id] += 1

    # Save permanently
    save_data()

    member = guild.get_member(int(user_id))

    if not member:
        return

    invite_count = invite_data[user_id]

    # Check and give rewards
    await check_rewards(member)

    # Find log channel
    log_channel = guild.get_channel(INVITE_LOG_CHANNEL_ID)

    if not log_channel:
        print(
            f"Could not find invite log channel: "
            f"{INVITE_LOG_CHANNEL_ID}"
        )
        return

    # -----------------------------------------------------
    # DETERMINE NEXT REWARD
    # -----------------------------------------------------

    if invite_count < 5:

        next_reward = (
            f"🎟️ **$5 OFF** — "
            f"{5 - invite_count} more invite(s)"
        )

    elif invite_count < 10:

        next_reward = (
            f"💵 **$10 OFF** — "
            f"{10 - invite_count} more invite(s)"
        )

    elif invite_count < 15:

        next_reward = (
            f"🍽️ **FREE MEAL** — "
            f"{15 - invite_count} more invite(s)"
        )

    else:

        next_reward = "🍽️ **FREE MEAL** — Maximum reward reached!"

    # -----------------------------------------------------
    # CREATE LOG EMBED
    # -----------------------------------------------------

    embed = discord.Embed(
        title="🎉 New Invite Detected!",
        description=(
            f"{member.mention} successfully invited "
            f"a new member to the server!"
        ),
        color=discord.Color.green()
    )

    embed.add_field(
        name="👤 Inviter",
        value=(
            f"{member.mention}\n"
            f"`{member.id}`"
        ),
        inline=True
    )

    if invited_member:

        embed.add_field(
            name="🆕 New Member",
            value=(
                f"{invited_member.mention}\n"
                f"`{invited_member.id}`"
            ),
            inline=True
        )

    embed.add_field(
        name="🔢 Total Invites",
        value=f"**{invite_count}**",
        inline=True
    )

    embed.add_field(
        name="🎁 Next Reward",
        value=next_reward,
        inline=False
    )

    # -----------------------------------------------------
    # REWARD UNLOCK MESSAGE
    # -----------------------------------------------------

    if invite_count == 5:

        embed.add_field(
            name="🏆 Reward Unlocked!",
            value=(
                "🎟️ **$5 OFF**\n"
                "The 5-invite reward role has been added!"
            ),
            inline=False
        )

    elif invite_count == 10:

        embed.add_field(
            name="🏆 Reward Unlocked!",
            value=(
                "💵 **$10 OFF**\n"
                "The 10-invite reward role has been added!"
            ),
            inline=False
        )

    elif invite_count == 15:

        embed.add_field(
            name="🏆 Reward Unlocked!",
            value=(
                "🍽️ **FREE MEAL** 🔥\n"
                "The FREE MEAL reward role has been added!"
            ),
            inline=False
        )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    embed.set_footer(
        text="Invite Rewards • Invite tracking system"
    )

    await log_channel.send(
        embed=embed
    )


# =========================================================
# CHECK REWARDS
# =========================================================

async def check_rewards(member):

    invites = get_invites(member.id)

    # -----------------------------------------------------
    # 5 INVITES
    # -----------------------------------------------------

    if invites >= 5:

        role = member.guild.get_role(FIVE_INVITE_ROLE)

        if role and role not in member.roles:
            try:
                await member.add_roles(role)

            except discord.Forbidden:
                print(
                    f"Could not give 5 invite role to {member}"
                )

    # -----------------------------------------------------
    # 10 INVITES
    # -----------------------------------------------------

    if invites >= 10:

        role = member.guild.get_role(TEN_INVITE_ROLE)

        if role and role not in member.roles:
            try:
                await member.add_roles(role)

            except discord.Forbidden:
                print(
                    f"Could not give 10 invite role to {member}"
                )

    # -----------------------------------------------------
    # 15 INVITES
    # -----------------------------------------------------

    if invites >= 15:

        role = member.guild.get_role(FIFTEEN_INVITE_ROLE)

        if role and role not in member.roles:
            try:
                await member.add_roles(role)

            except discord.Forbidden:
                print(
                    f"Could not give 15 invite role to {member}"
                )


# =========================================================
# CACHE INVITES
# =========================================================

async def cache_guild_invites(guild):

    try:

        invites = await guild.invites()

        invite_cache[guild.id] = {
            invite.code: invite.uses
            for invite in invites
        }

        print(
            f"Cached {len(invites)} invites for {guild.name}"
        )

    except discord.Forbidden:

        print(
            f"Cannot view invites in {guild.name}. "
            "Make sure the bot has Manage Server."
        )


# =========================================================
# BOT READY
# =========================================================

@bot.event
async def on_ready():

    load_data()

    print("--------------------------------------")
    print(f"Logged in as {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print("--------------------------------------")

    # Cache invites for every server
    for guild in bot.guilds:
        await cache_guild_invites(guild)

    # Sync slash commands
    try:

        synced = await bot.tree.sync()

        print(
            f"Synced {len(synced)} slash commands."
        )

    except Exception as e:

        print(
            f"Slash command sync error: {e}"
        )


# =========================================================
# MEMBER JOIN
# =========================================================

@bot.event
async def on_member_join(member):

    guild = member.guild

    try:

        new_invites = await guild.invites()

        old_invites = invite_cache.get(
            guild.id,
            {}
        )

        inviter = None

        # Find the invite whose use count increased
        for invite in new_invites:

            old_uses = old_invites.get(
                invite.code,
                0
            )

            if invite.uses > old_uses:

                inviter = invite.inviter
                break

        # Update invite cache
        invite_cache[guild.id] = {
            invite.code: invite.uses
            for invite in new_invites
        }

        # No inviter found
        if inviter is None:

            print(
                f"Could not determine inviter for "
                f"{member}"
            )

            return

        # Don't count self-invites
        if inviter.id == member.id:
            return

        # Add invite
await add_invite(
    guild,
    inviter.id,
    member
)
        )

        print(
            f"{inviter} invited {member}"
        )

    except Exception as e:

        print(
            f"Invite tracking error: {e}"
        )


# =========================================================
# /INVITES
# =========================================================

@bot.tree.command(
    name="invites",
    description="Check your invite count and reward progress."
)
async def invites_command(interaction: discord.Interaction):

    member = interaction.user

    invites = get_invites(member.id)

    # Determine next reward
    if invites < 5:

        next_amount = 5
        remaining = 5 - invites
        reward = "$5 OFF"

    elif invites < 10:

        next_amount = 10
        remaining = 10 - invites
        reward = "$10 OFF"

    elif invites < 15:

        next_amount = 15
        remaining = 15 - invites
        reward = "FREE MEAL"

    else:

        next_amount = 15
        remaining = 0
        reward = "FREE MEAL — YOU REACHED THE MAX REWARD!"

    # Progress bar
    if invites >= 15:

        progress = "████████████████████"

    else:

        progress_length = 20
        filled = int(
            min(invites, 15) / 15 * progress_length
        )

        progress = (
            "█" * filled +
            "░" * (progress_length - filled)
        )

    embed = discord.Embed(
        title="🎟️ Your Invite Rewards",
        description=(
            f"Hey {member.mention}! Here's your current "
            f"invite progress.\n\n"
            "Invite friends to the server and unlock "
            "exclusive rewards."
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="👥 Your Invites",
        value=f"**{invites}** successful invite(s)",
        inline=True
    )

    embed.add_field(
        name="🎁 Next Reward",
        value=(
            f"**{reward}**\n"
            f"{remaining} more invite(s)"
        ),
        inline=True
    )

    embed.add_field(
        name="📊 Progress",
        value=(
            f"`{progress}`\n"
            f"**{invites}/15 invites**"
        ),
        inline=False
    )

    embed.add_field(
        name="🏆 Reward Levels",
        value=(
            "🎟️ **5 Invites** → **$5 OFF**\n"
            "💵 **10 Invites** → **$10 OFF**\n"
            "🍽️ **15 Invites** → **FREE MEAL**"
        ),
        inline=False
    )

    embed.set_footer(
        text="Invite real members • Earn rewards • Enjoy the perks!"
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# =========================================================
# /REWARDS
# =========================================================

@bot.tree.command(
    name="rewards",
    description="Display the server invite reward information."
)
async def rewards_command(interaction: discord.Interaction):

    member = interaction.user

    # Check admin/staff role
    role = interaction.guild.get_role(
        REWARDS_ADMIN_ROLE_ID
    )

    if role not in member.roles:

        await interaction.response.send_message(
            "❌ You do not have permission to use this command.",
            ephemeral=True
        )

        return

    # Main embed
    embed = discord.Embed(
        title="🎉 INVITE REWARDS PROGRAM",
        description=(
            "## 🚀 Invite Friends. Earn Rewards.\n\n"
            "Want to save money or earn a **FREE MEAL**? "
            "Invite people to the server and climb through "
            "the reward levels!\n\n"
            "Every successful invite brings you closer to "
            "your next reward. Your progress is tracked "
            "automatically by the bot.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=discord.Color.gold()
    )

    embed.add_field(
        name="🎟️ LEVEL 1 — 5 INVITES",
        value=(
            "**Reward: $5 OFF**\n\n"
            "Invite **5 people** who successfully join "
            "the server and you'll receive the **$5 OFF** "
            "reward role automatically.\n\n"
            f"Role: <@&{FIVE_INVITE_ROLE}>"
        ),
        inline=False
    )

    embed.add_field(
        name="💵 LEVEL 2 — 10 INVITES",
        value=(
            "**Reward: $10 OFF**\n\n"
            "Reach **10 successful invites** and unlock "
            "the **$10 OFF** reward.\n\n"
            f"Role: <@&{TEN_INVITE_ROLE}>"
        ),
        inline=False
    )

    embed.add_field(
        name="🍽️ LEVEL 3 — 15 INVITES",
        value=(
            "**Reward: FREE MEAL** 🔥\n\n"
            "Reach **15 successful invites** and unlock "
            "the **FREE MEAL** reward role.\n\n"
            f"Role: <@&{FIFTEEN_INVITE_ROLE}>"
        ),
        inline=False
    )

    embed.add_field(
        name="📌 HOW IT WORKS",
        value=(
            "1️⃣ Create or use your personal Discord invite.\n"
            "2️⃣ Send your invite to your friends.\n"
            "3️⃣ They join the server through your invite.\n"
            "4️⃣ The bot automatically tracks the invite.\n"
            "5️⃣ Reach a reward level and receive the role.\n\n"
            "Use **/invites** at any time to see your "
            "current progress."
        ),
        inline=False
    )

    embed.add_field(
        name="⚠️ IMPORTANT",
        value=(
            "Only **successful server joins** count toward "
            "your invite total. The system is designed to "
            "track actual invites rather than simply "
            "creating invite links."
        ),
        inline=False
    )

    embed.set_footer(
        text="Invite more • Unlock more • Enjoy your rewards 🎉"
    )

    # Optional thumbnail
    embed.set_thumbnail(
        url=interaction.guild.icon.url
        if interaction.guild.icon
        else discord.Embed.Empty
    )

    await interaction.response.send_message(
        embed=embed
    )


# =========================================================
# /HELP
# =========================================================

@bot.tree.command(
    name="help",
    description="Learn how the invite reward system works."
)
async def help_command(interaction: discord.Interaction):

    embed = discord.Embed(
        title="📖 Invite Rewards Help",
        description=(
            "Welcome to the **Invite Rewards System**!\n\n"
            "You can earn rewards simply by inviting new "
            "members to the server.\n\n"
            "Below you'll find everything you need to know."
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="🔎 How do I check my invites?",
        value=(
            "Use **/invites**.\n\n"
            "The bot will show your total invites, your "
            "current progress bar, your next reward, and "
            "how many more people you need to invite."
        ),
        inline=False
    )

    embed.add_field(
        name="🎟️ What are the rewards?",
        value=(
            "**5 Invites** → 💵 **$5 OFF**\n"
            "**10 Invites** → 💵 **$10 OFF**\n"
            "**15 Invites** → 🍽️ **FREE MEAL**"
        ),
        inline=False
    )

    embed.add_field(
        name="🤖 How does tracking work?",
        value=(
            "When someone joins through your Discord invite, "
            "the bot checks which invite was used and adds "
            "the successful invite to your total."
        ),
        inline=False
    )

    embed.add_field(
        name="🏆 What happens when I reach a reward?",
        value=(
            "Your reward role is automatically added when "
            "you reach the required number of successful "
            "invites."
        ),
        inline=False
    )

    embed.add_field(
        name="📈 Want to keep earning?",
        value=(
            "Keep inviting new members! Once you reach "
            "**15 invites**, you've unlocked the current "
            "**FREE MEAL** reward."
        ),
        inline=False
    )

    embed.set_footer(
        text="Use /invites to check your progress anytime."
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# =========================================================
# ERROR HANDLING
# =========================================================

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error
):

    if isinstance(
        error,
        app_commands.CommandOnCooldown
    ):

        await interaction.response.send_message(
            "⏳ Please wait before using that command again.",
            ephemeral=True
        )

    else:

        print(
            f"Command error: {error}"
        )

        if not interaction.response.is_done():

            await interaction.response.send_message(
                "❌ Something went wrong while running that command.",
                ephemeral=True
            )


# =========================================================
# START BOT
# =========================================================

if not TOKEN:

    raise RuntimeError(
        "DISCORD_TOKEN environment variable is not set."
    )

bot.run(TOKEN)
