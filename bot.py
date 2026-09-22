import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone
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
# ACCOUNT AGE PROTECTION
# =========================================================

# Accounts younger than this will NOT count as an invite.
MINIMUM_ACCOUNT_AGE_DAYS = 7

# Accounts younger than this get a stronger warning.
VERY_NEW_ACCOUNT_HOURS = 24


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

# Stores:
#
# guild_id:
#     member_id:
#         inviter_id
#
# This lets us know who invited someone when they leave.
#
invite_records = {}

# Stores Discord invite uses.
invite_cache = {}


# =========================================================
# FILE HELPERS
# =========================================================

def load_json(filename, default):

    try:

        with open(filename, "r") as file:
            return json.load(file)

    except FileNotFoundError:

        return default

    except json.JSONDecodeError:

        print(f"{filename} is corrupted. Starting fresh.")

        return default


def save_json(filename, data):

    try:

        with open(filename, "w") as file:
            json.dump(
                data,
                file,
                indent=4
            )

    except Exception as e:

        print(
            f"Could not save {filename}: {e}"
        )


# =========================================================
# LOAD DATA
# =========================================================

def load_data():

    global invite_data
    global invite_records

    invite_data = load_json(
        "invite_data.json",
        {}
    )

    invite_records = load_json(
        "invite_records.json",
        {}
    )

    print("Invite data loaded.")
    print("Invite records loaded.")


# =========================================================
# SAVE DATA
# =========================================================

def save_data():

    save_json(
        "invite_data.json",
        invite_data
    )

    save_json(
        "invite_records.json",
        invite_records
    )


# =========================================================
# GET INVITES
# =========================================================

def get_invites(user_id):

    return int(
        invite_data.get(
            str(user_id),
            0
        )
    )


# =========================================================
# ACCOUNT AGE
# =========================================================

def get_account_age(member):

    now = datetime.now(timezone.utc)

    created_at = member.created_at

    age = now - created_at

    return age


def get_account_age_text(member):

    age = get_account_age(member)

    days = age.days

    hours = age.seconds // 3600

    if days > 0:

        return f"{days} day(s), {hours} hour(s)"

    return f"{hours} hour(s)"


def is_account_too_new(member):

    age = get_account_age(member)

    return age.total_seconds() < (
        MINIMUM_ACCOUNT_AGE_DAYS * 86400
    )


def is_very_new_account(member):

    age = get_account_age(member)

    return age.total_seconds() < (
        VERY_NEW_ACCOUNT_HOURS * 3600
    )


# =========================================================
# ACCOUNT STATUS
# =========================================================

def get_account_status(member):

    if is_very_new_account(member):

        return (
            "🚨 **VERY NEW ACCOUNT**\n"
            "Account is less than 24 hours old."
        )

    if is_account_too_new(member):

        return (
            "⚠️ **NEW ACCOUNT**\n"
            f"Account is younger than "
            f"{MINIMUM_ACCOUNT_AGE_DAYS} days."
        )

    return (
        "✅ **ACCOUNT AGE OK**\n"
        "Account meets the minimum age requirement."
    )


# =========================================================
# PROGRESS BAR
# =========================================================

def make_progress_bar(invites):

    maximum = 15
    bar_length = 20

    percentage = min(invites, maximum) / maximum

    filled = int(
        percentage * bar_length
    )

    empty = bar_length - filled

    return (
        "█" * filled +
        "░" * empty
    )


# =========================================================
# NEXT REWARD
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
        "You've reached the maximum reward."
    )


# =========================================================
# UPDATE REWARD ROLES
# =========================================================

async def update_reward_roles(member):

    invites = get_invites(member.id)

    changes = []

    five_role = member.guild.get_role(
        FIVE_INVITE_ROLE
    )

    ten_role = member.guild.get_role(
        TEN_INVITE_ROLE
    )

    fifteen_role = member.guild.get_role(
        FIFTEEN_INVITE_ROLE
    )

    # -----------------------------------------------------
    # 5 INVITES
    # -----------------------------------------------------

    if five_role:

        if invites >= 5:

            if five_role not in member.roles:

                try:

                    await member.add_roles(
                        five_role
                    )

                    changes.append(
                        "🎟️ **$5 OFF** role added"
                    )

                except discord.Forbidden:

                    print(
                        f"Cannot add $5 role to {member}"
                    )

        else:

            if five_role in member.roles:

                try:

                    await member.remove_roles(
                        five_role
                    )

                    changes.append(
                        "🎟️ **$5 OFF** role removed"
                    )

                except discord.Forbidden:

                    print(
                        f"Cannot remove $5 role from {member}"
                    )

    # -----------------------------------------------------
    # 10 INVITES
    # -----------------------------------------------------

    if ten_role:

        if invites >= 10:

            if ten_role not in member.roles:

                try:

                    await member.add_roles(
                        ten_role
                    )

                    changes.append(
                        "💵 **$10 OFF** role added"
                    )

                except discord.Forbidden:

                    print(
                        f"Cannot add $10 role to {member}"
                    )

        else:

            if ten_role in member.roles:

                try:

                    await member.remove_roles(
                        ten_role
                    )

                    changes.append(
                        "💵 **$10 OFF** role removed"
                    )

                except discord.Forbidden:

                    print(
                        f"Cannot remove $10 role from {member}"
                    )

    # -----------------------------------------------------
    # 15 INVITES
    # -----------------------------------------------------

    if fifteen_role:

        if invites >= 15:

            if fifteen_role not in member.roles:

                try:

                    await member.add_roles(
                        fifteen_role
                    )

                    changes.append(
                        "🍽️ **FREE MEAL** role added"
                    )

                except discord.Forbidden:

                    print(
                        f"Cannot add FREE MEAL role to {member}"
                    )

        else:

            if fifteen_role in member.roles:

                try:

                    await member.remove_roles(
                        fifteen_role
                    )

                    changes.append(
                        "🍽️ **FREE MEAL** role removed"
                    )

                except discord.Forbidden:

                    print(
                        f"Cannot remove FREE MEAL role from {member}"
                    )

    return changes


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
            f"Cached {len(invites)} invites "
            f"for {guild.name}"
        )

    except discord.Forbidden:

        print(
            f"Cannot access invites in "
            f"{guild.name}."
        )

    except Exception as e:

        print(
            f"Invite cache error: {e}"
        )


# =========================================================
# BOT READY
# =========================================================

@bot.event
async def on_ready():

    load_data()

    print("----------------------------------------")
    print(f"Logged in as {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print("----------------------------------------")

    for guild in bot.guilds:

        await cache_guild_invites(
            guild
        )

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

        current_invites = await guild.invites()

        old_invites = invite_cache.get(
            guild.id,
            {}
        )

        inviter = None

        # -------------------------------------------------
        # FIND USED INVITE
        # -------------------------------------------------

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

        # -------------------------------------------------
        # LOG CHANNEL
        # -------------------------------------------------

        log_channel = guild.get_channel(
            INVITE_LOG_CHANNEL_ID
        )

        # -------------------------------------------------
        # NO INVITER FOUND
        # -------------------------------------------------

        if inviter is None:

            if log_channel:

                embed = discord.Embed(
                    title="👤 MEMBER JOINED",
                    description=(
                        f"{member.mention} joined the server.\n\n"
                        "⚠️ The bot could not determine "
                        "which invite was used."
                    ),
                    color=discord.Color.orange()
                )

                embed.add_field(
                    name="📅 Account Age",
                    value=get_account_age_text(
                        member
                    ),
                    inline=True
                )

                embed.add_field(
                    name="🛡️ Account Status",
                    value=get_account_status(
                        member
                    ),
                    inline=True
                )

                embed.set_thumbnail(
                    url=member.display_avatar.url
                )

                await log_channel.send(
                    embed=embed
                )

            return

        # -------------------------------------------------
        # SELF INVITE
        # -------------------------------------------------

        if inviter.id == member.id:

            print(
                f"Self invite detected: {member}"
            )

            return

        # -------------------------------------------------
        # ACCOUNT AGE PROTECTION
        # -------------------------------------------------

        account_too_new = is_account_too_new(
            member
        )

        # -------------------------------------------------
        # STORE WHO INVITED THEM
        # -------------------------------------------------

        guild_id = str(
            guild.id
        )

        member_id = str(
            member.id
        )

        inviter_id = str(
            inviter.id
        )

        if guild_id not in invite_records:

            invite_records[guild_id] = {}

        invite_records[guild_id][member_id] = {
            "inviter_id": inviter_id,
            "counted": not account_too_new,
            "account_created": member.created_at.isoformat()
        }

        # -------------------------------------------------
        # IF ACCOUNT IS TOO NEW
        # -------------------------------------------------

        if account_too_new:

            save_data()

            if log_channel:

                if is_very_new_account(member):

                    status = (
                        "🚨 **VERY NEW ACCOUNT**\n"
                        "This account is less than 24 hours old."
                    )

                    log_color = discord.Color.red()

                else:

                    status = (
                        "⚠️ **NEW ACCOUNT**\n"
                        f"This account is younger than "
                        f"{MINIMUM_ACCOUNT_AGE_DAYS} days."
                    )

                    log_color = discord.Color.orange()

                embed = discord.Embed(
                    title="🛡️ SUSPICIOUS / NEW ACCOUNT",
                    description=(
                        f"{member.mention} joined using "
                        f"{inviter.mention}'s invite.\n\n"
                        "The invite was **NOT counted** because "
                        "the account does not meet the minimum "
                        "account-age requirement."
                    ),
                    color=log_color
                )

                embed.add_field(
                    name="👤 New Member",
                    value=member.mention,
                    inline=True
                )

                embed.add_field(
                    name="🎟️ Inviter",
                    value=inviter.mention,
                    inline=True
                )

                embed.add_field(
                    name="📅 Account Age",
                    value=get_account_age_text(
                        member
                    ),
                    inline=True
                )

                embed.add_field(
                    name="🛡️ Security Check",
                    value=status,
                    inline=False
                )

                embed.add_field(
                    name="❌ Invite Counted?",
                    value="**NO**",
                    inline=True
                )

                embed.set_thumbnail(
                    url=member.display_avatar.url
                )

                embed.set_footer(
                    text="Invite Security System"
                )

                await log_channel.send(
                    embed=embed
                )

            return

        # -------------------------------------------------
        # VALID INVITE
        # -------------------------------------------------

        if inviter_id not in invite_data:

            invite_data[inviter_id] = 0

        old_count = get_invites(
            inviter.id
        )

        invite_data[inviter_id] = old_count + 1

        new_count = get_invites(
            inviter.id
        )

        save_data()

        # Update reward roles
        reward_changes = await update_reward_roles(
            inviter
        )

        # -------------------------------------------------
        # SEND LOG
        # -------------------------------------------------

        if log_channel:

            embed = discord.Embed(
                title="🎉 VALID INVITE DETECTED",
                description=(
                    f"{inviter.mention} invited "
                    f"{member.mention}!\n\n"
                    "The invite has been counted toward "
                    "their reward progress."
                ),
                color=discord.Color.green()
            )

            embed.add_field(
                name="👤 Inviter",
                value=inviter.mention,
                inline=True
            )

            embed.add_field(
                name="🆕 New Member",
                value=member.mention,
                inline=True
            )

            embed.add_field(
                name="🔢 Invite Total",
                value=(
                    f"**{old_count} → {new_count}**"
                ),
                inline=True
            )

            embed.add_field(
                name="📅 Account Age",
                value=get_account_age_text(
                    member
                ),
                inline=True
            )

            embed.add_field(
                name="🛡️ Account Status",
                value="✅ Account age accepted",
                inline=True
            )

            embed.add_field(
                name="📊 Progress",
                value=(
                    f"`{make_progress_bar(new_count)}`\n"
                    f"**{min(new_count, 15)}/15**"
                ),
                inline=False
            )

            embed.add_field(
                name="🎁 Next Reward",
                value=get_next_reward(
                    new_count
                ),
                inline=False
            )

            if reward_changes:

                embed.add_field(
                    name="🏆 REWARD UPDATE",
                    value="\n".join(
                        reward_changes
                    ),
                    inline=False
                )

            embed.set_thumbnail(
                url=inviter.display_avatar.url
            )

            embed.set_footer(
                text="Invite Security & Rewards System"
            )

            await log_channel.send(
                embed=embed
            )

        print(
            f"{inviter} invited {member}. "
            f"Total: {new_count}"
        )

    except discord.Forbidden:

        print(
            "Discord denied access while "
            "checking invites."
        )

    except Exception as e:

        print(
            f"Member join error: {e}"
        )


# =========================================================
# MEMBER LEAVE
# =========================================================

@bot.event
async def on_member_remove(member):

    guild = member.guild

    guild_id = str(
        guild.id
    )

    member_id = str(
        member.id
    )

    # Check whether this member was recorded
    if guild_id not in invite_records:

        return

    if member_id not in invite_records[guild_id]:

        return

    record = invite_records[guild_id][member_id]

    inviter_id = int(
        record["inviter_id"]
    )

    counted = record.get(
        "counted",
        False
    )

    # Remove the record
    del invite_records[guild_id][member_id]

    save_data()

    # If the invite never counted, nothing to remove
    if not counted:

        return

    # -----------------------------------------------------
    # REMOVE INVITE FROM INVITER
    # -----------------------------------------------------

    old_count = get_invites(
        inviter_id
    )

    if old_count <= 0:

        return

    new_count = old_count - 1

    invite_data[str(inviter_id)] = new_count

    save_data()

    inviter = guild.get_member(
        inviter_id
    )

    # -----------------------------------------------------
    # UPDATE REWARD ROLES
    # -----------------------------------------------------

    reward_changes = []

    if inviter:

        reward_changes = await update_reward_roles(
            inviter
        )

    # -----------------------------------------------------
    # LOG LEAVE
    # -----------------------------------------------------

    log_channel = guild.get_channel(
        INVITE_LOG_CHANNEL_ID
    )

    if not log_channel:

        return

    embed = discord.Embed(
        title="🚪 INVITED MEMBER LEFT",
        description=(
            f"**{member}** has left the server.\n\n"
            "Because this member was invited by another "
            "member, their invite has been removed from "
            "the inviter's total."
        ),
        color=discord.Color.red()
    )

    embed.add_field(
        name="🆕 Member Who Left",
        value=(
            f"{member.mention}\n"
            f"`{member.id}`"
        ),
        inline=True
    )

    if inviter:

        embed.add_field(
            name="👤 Original Inviter",
            value=(
                f"{inviter.mention}\n"
                f"`{inviter.id}`"
            ),
            inline=True
        )

    else:

        embed.add_field(
            name="👤 Original Inviter",
            value=f"`{inviter_id}`",
            inline=True
        )

    embed.add_field(
        name="📉 Invite Count",
        value=(
            f"**{old_count} → {new_count}**"
        ),
        inline=True
    )

    embed.add_field(
        name="🎁 Current Reward Progress",
        value=(
            f"`{make_progress_bar(new_count)}`\n"
            f"**{min(new_count, 15)}/15 invites**"
        ),
        inline=False
    )

    if inviter:

        embed.add_field(
            name="🏆 Reward Role Changes",
            value=(
                "\n".join(reward_changes)
                if reward_changes
                else "No reward roles changed."
            ),
            inline=False
        )

    embed.set_footer(
        text="Invite Security System • Invite removed"
    )

    await log_channel.send(
        embed=embed
    )

    print(
        f"{member} left. Removed 1 invite "
        f"from {inviter_id}."
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

    invites = get_invites(
        member.id
    )

    embed = discord.Embed(
        title="🎟️ YOUR INVITE REWARDS",
        description=(
            f"Welcome, {member.mention}! 👋\n\n"
            "Here is your current invite progress.\n\n"
            "Only valid invites from accounts that meet "
            "the server's security requirements count."
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
        value=get_next_reward(
            invites
        ),
        inline=True
    )

    embed.add_field(
        name="📊 Progress",
        value=(
            f"`{make_progress_bar(invites)}`\n"
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

    embed.add_field(
        name="🛡️ INVITE SECURITY",
        value=(
            f"Accounts younger than "
            f"**{MINIMUM_ACCOUNT_AGE_DAYS} days** "
            "do not count toward invite rewards."
        ),
        inline=False
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    embed.set_footer(
        text="Invite Rewards • Use /help for more information"
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

    if interaction.guild is None:

        await interaction.response.send_message(
            "❌ This command can only be used inside the server.",
            ephemeral=True
        )

        return

    staff_role = interaction.guild.get_role(
        REWARDS_ADMIN_ROLE_ID
    )

    if staff_role is None:

        await interaction.response.send_message(
            "❌ The reward staff role could not be found.",
            ephemeral=True
        )

        return

    if staff_role not in member.roles:

        await interaction.response.send_message(
            "❌ You do not have permission to use `/rewards`.",
            ephemeral=True
        )

        return

    embed = discord.Embed(
        title="🎉 INVITE REWARDS PROGRAM",
        description=(
            "## 🚀 Invite Friends. Earn Rewards.\n\n"
            "Bring new members into the server and unlock "
            "exclusive rewards based on your successful "
            "invite count.\n\n"
            "The bot automatically tracks your invites and "
            "manages your reward roles.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=discord.Color.gold()
    )

    embed.add_field(
        name="🎟️ LEVEL 1 — 5 INVITES",
        value=(
            "### 💵 $5 OFF\n\n"
            "Reach **5 valid invites** and receive the "
            "**$5 OFF** reward.\n\n"
            f"Role: <@&{FIVE_INVITE_ROLE}>"
        ),
        inline=False
    )

    embed.add_field(
        name="💵 LEVEL 2 — 10 INVITES",
        value=(
            "### 💰 $10 OFF\n\n"
            "Reach **10 valid invites** and receive the "
            "**$10 OFF** reward.\n\n"
            f"Role: <@&{TEN_INVITE_ROLE}>"
        ),
        inline=False
    )

    embed.add_field(
        name="🍽️ LEVEL 3 — 15 INVITES",
        value=(
            "### 🔥 FREE MEAL\n\n"
            "Reach **15 valid invites** and unlock the "
            "**FREE MEAL** reward.\n\n"
            f"Role: <@&{FIFTEEN_INVITE_ROLE}>"
        ),
        inline=False
    )

    embed.add_field(
        name="🛡️ INVITE SECURITY",
        value=(
            f"Accounts younger than "
            f"**{MINIMUM_ACCOUNT_AGE_DAYS} days** "
            "are flagged as new and do not count toward "
            "rewards.\n\n"
            "If an invited member later leaves the server, "
            "their invite is automatically removed."
        ),
        inline=False
    )

    embed.add_field(
        name="📌 HOW IT WORKS",
        value=(
            "1️⃣ Share your Discord invite.\n"
            "2️⃣ Your friend joins.\n"
            "3️⃣ The bot checks the invite.\n"
            "4️⃣ The account passes the security check.\n"
            "5️⃣ Your invite count increases.\n"
            "6️⃣ Your reward role updates automatically.\n\n"
            "Use **/invites** to track your progress."
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
            "Invite new members, earn rewards, and track "
            "your progress with the commands below."
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="📊 /invites",
        value=(
            "Shows your current valid invite count, "
            "progress bar, and next reward."
        ),
        inline=False
    )

    embed.add_field(
        name="🎁 /rewards",
        value=(
            "Shows the complete reward program. "
            "This command is restricted to authorized staff."
        ),
        inline=False
    )

    embed.add_field(
        name="❓ /help",
        value=(
            "Shows this help menu and explains how "
            "the reward system works."
        ),
        inline=False
    )

    embed.add_field(
        name="🏆 REWARDS",
        value=(
            "🎟️ **5 Invites** → **$5 OFF**\n"
            "💵 **10 Invites** → **$10 OFF**\n"
            "🍽️ **15 Invites** → **FREE MEAL**"
        ),
        inline=False
    )

    embed.add_field(
        name="🛡️ ALT / NEW ACCOUNT PROTECTION",
        value=(
            f"Accounts younger than "
            f"**{MINIMUM_ACCOUNT_AGE_DAYS} days** "
            "do not count toward invite rewards.\n\n"
            "Accounts under **24 hours** are given an "
            "extra warning in the security log.\n\n"
            "The system flags suspicious account age, but "
            "account age alone cannot prove that an account "
            "is an alt."
        ),
        inline=False
    )

    embed.add_field(
        name="🚪 WHAT IF SOMEONE LEAVES?",
        value=(
            "If someone you invited leaves the server, "
            "the bot automatically removes their invite "
            "from your total.\n\n"
            "If that causes you to fall below a reward "
            "level, the corresponding reward role is "
            "automatically removed."
        ),
        inline=False
    )

    embed.set_footer(
        text="Invite Rewards & Security System"
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# =========================================================
# ERROR HANDLER
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
