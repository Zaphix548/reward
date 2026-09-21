import discord
from discord.ext import commands
from discord import app_commands
import json
import os

# =========================================================
# CONFIG
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

# Staff role allowed to use /rewards
REWARDS_ADMIN_ROLE_ID = 1547436901428891660

# Invite log channel
INVITE_LOG_CHANNEL_ID = 1542342156428255242

# Reward roles
FIVE_INVITE_ROLE = 1551687592678793246
TEN_INVITE_ROLE = 1551687732953088091
FIFTEEN_INVITE_ROLE = 1551688333443465347

# =========================================================
# BOT SETUP
# =========================================================

intents = discord.Intents.default()
intents.guilds = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# =========================================================
# DATA
# =========================================================

invite_data = {}
invite_cache = {}


# =========================================================
# LOAD DATA
# =========================================================

def load_data():
    global invite_data

    try:
        with open("invite_data.json", "r") as file:
            invite_data = json.load(file)

        print("Invite data loaded successfully.")

    except FileNotFoundError:
        invite_data = {}
        print("No invite data file found. Starting fresh.")

    except json.JSONDecodeError:
        invite_data = {}
        print("Invite data file was corrupted. Starting fresh.")


# =========================================================
# SAVE DATA
# =========================================================

def save_data():
    try:
        with open("invite_data.json", "w") as file:
            json.dump(invite_data, file, indent=4)

    except Exception as e:
        print(f"Could not save invite data: {e}")


# =========================================================
# GET INVITES
# =========================================================

def get_invites(user_id):
    return int(invite_data.get(str(user_id), 0))


# =========================================================
# GET NEXT REWARD
# =========================================================

def get_next_reward(invites):

    if invites < 5:
        return (
            "🎟️ **$5 OFF**\n"
            f"**{5 - invites}** more invite(s) needed."
        )

    if invites < 10:
        return (
            "💵 **$10 OFF**\n"
            f"**{10 - invites}** more invite(s) needed."
        )

    if invites < 15:
        return (
            "🍽️ **FREE MEAL**\n"
            f"**{15 - invites}** more invite(s) needed."
        )

    return (
        "🏆 **FREE MEAL UNLOCKED!**\n"
        "You've reached the maximum reward level."
    )


# =========================================================
# PROGRESS BAR
# =========================================================

def make_progress_bar(invites):

    maximum = 15
    bar_length = 20

    percentage = min(invites, maximum) / maximum

    filled = int(percentage * bar_length)
    empty = bar_length - filled

    return "█" * filled + "░" * empty


# =========================================================
# CHECK AND GIVE REWARDS
# =========================================================

async def check_rewards(member):

    invites = get_invites(member.id)

    unlocked_rewards = []

    # -----------------------------------------------------
    # 5 INVITES
    # -----------------------------------------------------

    if invites >= 5:

        role = member.guild.get_role(FIVE_INVITE_ROLE)

        if role and role not in member.roles:

            try:
                await member.add_roles(role)
                unlocked_rewards.append("🎟️ **$5 OFF**")

            except discord.Forbidden:
                print(
                    f"Missing permission to give 5-invite role "
                    f"to {member}"
                )

    # -----------------------------------------------------
    # 10 INVITES
    # -----------------------------------------------------

    if invites >= 10:

        role = member.guild.get_role(TEN_INVITE_ROLE)

        if role and role not in member.roles:

            try:
                await member.add_roles(role)
                unlocked_rewards.append("💵 **$10 OFF**")

            except discord.Forbidden:
                print(
                    f"Missing permission to give 10-invite role "
                    f"to {member}"
                )

    # -----------------------------------------------------
    # 15 INVITES
    # -----------------------------------------------------

    if invites >= 15:

        role = member.guild.get_role(FIFTEEN_INVITE_ROLE)

        if role and role not in member.roles:

            try:
                await member.add_roles(role)
                unlocked_rewards.append("🍽️ **FREE MEAL**")

            except discord.Forbidden:
                print(
                    f"Missing permission to give 15-invite role "
                    f"to {member}"
                )

    return unlocked_rewards


# =========================================================
# ADD INVITE
# =========================================================

async def add_invite(guild, inviter_id, invited_member):

    user_id = str(inviter_id)

    if user_id not in invite_data:
        invite_data[user_id] = 0

    # Add one successful invite
    invite_data[user_id] += 1

    # Save immediately
    save_data()

    inviter = guild.get_member(inviter_id)

    if inviter is None:
        return

    new_total = get_invites(inviter.id)

    # Give reward roles
    unlocked_rewards = await check_rewards(inviter)

    # Find log channel
    log_channel = guild.get_channel(
        INVITE_LOG_CHANNEL_ID
    )

    if log_channel is None:

        print(
            f"Invite log channel "
            f"{INVITE_LOG_CHANNEL_ID} was not found."
        )

        return

    # -----------------------------------------------------
    # CREATE LOG EMBED
    # -----------------------------------------------------

    embed = discord.Embed(
        title="🎉 NEW INVITE DETECTED",
        description=(
            f"{inviter.mention} just invited "
            f"{invited_member.mention} to the server!\n\n"
            "The invite has been successfully counted "
            "toward their reward progress."
        ),
        color=discord.Color.green()
    )

    embed.add_field(
        name="👤 Inviter",
        value=(
            f"{inviter.mention}\n"
            f"`{inviter.id}`"
        ),
        inline=True
    )

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
        value=f"**{new_total}**",
        inline=True
    )

    embed.add_field(
        name="📊 Progress",
        value=(
            f"`{make_progress_bar(new_total)}`\n"
            f"**{min(new_total, 15)}/15 invites**"
        ),
        inline=False
    )

    embed.add_field(
        name="🎁 Next Reward",
        value=get_next_reward(new_total),
        inline=False
    )

    # -----------------------------------------------------
    # REWARD UNLOCKED
    # -----------------------------------------------------

    if unlocked_rewards:

        embed.add_field(
            name="🏆 REWARD UNLOCKED!",
            value=(
                "Congratulations!\n\n"
                + "\n".join(unlocked_rewards)
                + "\n\nThe reward role has been automatically "
                "added to their account."
            ),
            inline=False
        )

    embed.set_thumbnail(
        url=inviter.display_avatar.url
    )

    embed.set_footer(
        text="Invite Rewards System • Automatic Tracking"
    )

    try:
        await log_channel.send(embed=embed)

    except discord.Forbidden:
        print(
            "Bot does not have permission to send messages "
            "in the invite log channel."
        )


# =========================================================
# CACHE SERVER INVITES
# =========================================================

async def cache_guild_invites(guild):

    try:

        invites = await guild.invites()

        invite_cache[guild.id] = {
            invite.code: invite.uses
            for invite in invites
        }

        print(
            f"Cached {len(invites)} invites "
            f"for {guild.name}"
        )

    except discord.Forbidden:

        print(
            f"Cannot access invites for {guild.name}."
        )

    except Exception as e:

        print(
            f"Error caching invites for "
            f"{guild.name}: {e}"
        )


# =========================================================
# BOT READY
# =========================================================

@bot.event
async def on_ready():

    load_data()

    print("----------------------------------------")
    print(f"Bot logged in as: {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print("----------------------------------------")

    # Cache invites
    for guild in bot.guilds:
        await cache_guild_invites(guild)

    # Sync slash commands
    try:

        synced = await bot.tree.sync()

        print(
            f"Successfully synced "
            f"{len(synced)} slash commands."
        )

    except Exception as e:

        print(
            f"Slash command sync failed: {e}"
        )


# =========================================================
# MEMBER JOIN
# =========================================================

@bot.event
async def on_member_join(member):

    guild = member.guild

    try:

        # Get current invites
        current_invites = await guild.invites()

        # Get old cached invites
        old_invites = invite_cache.get(
            guild.id,
            {}
        )

        inviter = None

        # Find which invite increased
        for invite in current_invites:

            old_uses = old_invites.get(
                invite.code,
                0
            )

            if invite.uses > old_uses:

                inviter = invite.inviter
                break

        # Update cache
        invite_cache[guild.id] = {
            invite.code: invite.uses
            for invite in current_invites
        }

        # Could not determine inviter
        if inviter is None:

            print(
                f"Could not determine inviter for "
                f"{member}."
            )

            return

        # Prevent self-invite counting
        if inviter.id == member.id:

            print(
                f"Self-invite detected for {member}."
            )

            return

        # Add the successful invite
        await add_invite(
            guild,
            inviter.id,
            member
        )

        print(
            f"{inviter} invited {member}."
        )

    except discord.Forbidden:

        print(
            f"Missing permission to read invites "
            f"in {guild.name}."
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
async def invites_command(
    interaction: discord.Interaction
):

    member = interaction.user

    invites = get_invites(member.id)

    progress = make_progress_bar(invites)

    embed = discord.Embed(
        title="🎟️ YOUR INVITE REWARDS",
        description=(
            f"Welcome, {member.mention}! 👋\n\n"
            "This is your personal invite progress. "
            "Keep inviting new members to unlock "
            "bigger rewards.\n\n"
            "Your invites are tracked automatically "
            "whenever someone joins through your invite."
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="👥 Successful Invites",
        value=f"**{invites}**",
        inline=True
    )

    embed.add_field(
        name="🎁 Next Reward",
        value=get_next_reward(invites),
        inline=True
    )

    embed.add_field(
        name="📊 Overall Progress",
        value=(
            f"`{progress}`\n"
            f"**{min(invites, 15)}/15 invites**"
        ),
        inline=False
    )

    embed.add_field(
        name="🏆 REWARD LEVELS",
        value=(
            "🎟️ **5 Invites** → **$5 OFF**\n"
            "💵 **10 Invites** → **$10 OFF**\n"
            "🍽️ **15 Invites** → **FREE MEAL**"
        ),
        inline=False
    )

    if invites >= 15:

        embed.add_field(
            name="🔥 MAX REWARD REACHED!",
            value=(
                "You've reached **15 invites** and "
                "unlocked the **FREE MEAL** reward!"
            ),
            inline=False
        )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    embed.set_footer(
        text="Invite Rewards • Use /help to learn more"
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
async def rewards_command(
    interaction: discord.Interaction
):

    member = interaction.user

    # Check server
    if interaction.guild is None:

        await interaction.response.send_message(
            "❌ This command can only be used inside the server.",
            ephemeral=True
        )

        return

    # Get required staff role
    staff_role = interaction.guild.get_role(
        REWARDS_ADMIN_ROLE_ID
    )

    # Check permission
    if staff_role is None or staff_role not in member.roles:

        await interaction.response.send_message(
            "❌ You do not have permission to use `/rewards`.",
            ephemeral=True
        )

        return

    # -----------------------------------------------------
    # REWARDS EMBED
    # -----------------------------------------------------

    embed = discord.Embed(
        title="🎉 INVITE REWARDS PROGRAM",
        description=(
            "## 🚀 Invite Friends. Earn Rewards.\n\n"
            "Invite new members to the server and earn "
            "exclusive rewards based on how many successful "
            "invites you make.\n\n"
            "Your invite count is tracked automatically. "
            "Once you reach a reward level, the appropriate "
            "role will be added to you automatically.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=discord.Color.gold()
    )

    embed.add_field(
        name="🎟️ LEVEL 1 — 5 INVITES",
        value=(
            "### 💵 $5 OFF\n\n"
            "Reach **5 successful invites** and receive "
            "the **$5 OFF** reward.\n\n"
            f"🎟️ Reward Role: <@&{FIVE_INVITE_ROLE}>"
        ),
        inline=False
    )

    embed.add_field(
        name="💵 LEVEL 2 — 10 INVITES",
        value=(
            "### 💰 $10 OFF\n\n"
            "Reach **10 successful invites** and receive "
            "the **$10 OFF** reward.\n\n"
            f"💵 Reward Role: <@&{TEN_INVITE_ROLE}>"
        ),
        inline=False
    )

    embed.add_field(
        name="🍽️ LEVEL 3 — 15 INVITES",
        value=(
            "### 🔥 FREE MEAL\n\n"
            "Reach **15 successful invites** and unlock "
            "the **FREE MEAL** reward.\n\n"
            f"🍽️ Reward Role: <@&{FIFTEEN_INVITE_ROLE}>"
        ),
        inline=False
    )

    embed.add_field(
        name="📌 HOW IT WORKS",
        value=(
            "1️⃣ Create your Discord invite.\n"
            "2️⃣ Share it with your friends.\n"
            "3️⃣ Your friend joins the server.\n"
            "4️⃣ The bot detects which invite they used.\n"
            "5️⃣ Your invite total increases automatically.\n"
            "6️⃣ Your reward role is automatically added "
            "when you reach a milestone.\n\n"
            "Use **/invites** to check your progress."
        ),
        inline=False
    )

    embed.add_field(
        name="📈 TRACK YOUR PROGRESS",
        value=(
            "Use `/invites` anytime to see:\n\n"
            "👥 Your total successful invites\n"
            "📊 Your progress toward 15 invites\n"
            "🎁 Your next available reward\n"
            "🏆 Your reward levels"
        ),
        inline=False
    )

    embed.add_field(
        name="⚠️ IMPORTANT",
        value=(
            "Only actual members joining the server through "
            "your invite count toward your total. Creating "
            "invite links by itself does not increase your "
            "invite count."
        ),
        inline=False
    )

    if interaction.guild.icon:

        embed.set_thumbnail(
            url=interaction.guild.icon.url
        )

    embed.set_footer(
        text="Invite Rewards System • Invite • Earn • Enjoy"
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
async def help_command(
    interaction: discord.Interaction
):

    embed = discord.Embed(
        title="📖 INVITE REWARDS HELP",
        description=(
            "Welcome to the **Invite Rewards System**! 🎉\n\n"
            "This system lets you earn rewards by bringing "
            "new members into the server.\n\n"
            "Your successful invites are automatically "
            "tracked by the bot."
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="🔎 How do I check my invites?",
        value=(
            "Use **/invites**.\n\n"
            "You'll see your total invites, progress bar, "
            "next reward, and all available reward levels."
        ),
        inline=False
    )

    embed.add_field(
        name="🎁 What can I earn?",
        value=(
            "🎟️ **5 Invites** → **$5 OFF**\n"
            "💵 **10 Invites** → **$10 OFF**\n"
            "🍽️ **15 Invites** → **FREE MEAL**"
        ),
        inline=False
    )

    embed.add_field(
        name="🤖 How does invite tracking work?",
        value=(
            "When somebody joins the server, the bot checks "
            "which invite was used. If your invite was used, "
            "your successful invite count goes up by 1."
        ),
        inline=False
    )

    embed.add_field(
        name="🏆 What happens when I reach a reward?",
        value=(
            "You don't have to ask staff for the role. "
            "The bot automatically gives you the appropriate "
            "reward role once you reach the required number "
            "of successful invites."
        ),
        inline=False
    )

    embed.add_field(
        name="📊 Want to see your progress?",
        value=(
            "Type **/invites** whenever you want to see "
            "exactly how close you are to the next reward."
        ),
        inline=False
    )

    embed.add_field(
        name="💡 Quick Example",
        value=(
            "If you currently have **4 invites** and one "
            "more person joins using your invite, you'll "
            "reach **5 invites** and unlock the **$5 OFF** "
            "reward."
        ),
        inline=False
    )

    embed.set_footer(
        text="Invite more members • Unlock more rewards 🎉"
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# =========================================================
# COMMAND ERROR HANDLER
# =========================================================

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error
):

    print(
        f"Slash command error: {error}"
    )

    if interaction.response.is_done():
        return

    try:

        await interaction.response.send_message(
            "❌ Something went wrong while running "
            "that command.",
            ephemeral=True
        )

    except Exception:
        pass


# =========================================================
# START BOT
# =========================================================

if not TOKEN:

    raise RuntimeError(
        "DISCORD_TOKEN environment variable is not set."
    )

bot.run(TOKEN)
