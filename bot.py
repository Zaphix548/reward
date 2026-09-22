import discord
from discord.ext import commands
from discord import app_commands
import os
import json
from datetime import datetime, timezone, timedelta


# ============================================================
# INVITE REWARDS BOT v2.0
# ============================================================

print("========================================")
print("Invite Rewards Bot v2.0 STARTING...")
print("========================================")


# ============================================================
# CONFIG
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")

# Staff/admin role allowed to use /rewards
REWARDS_ADMIN_ROLE_ID = 1547436901428891660

# Invite log channel
INVITE_LOG_CHANNEL_ID = 1542342156428255242

# Reward roles
FIVE_INVITE_ROLE = 1551687592678793246
TEN_INVITE_ROLE = 1551687732953088091
FIFTEEN_INVITE_ROLE = 1551688333443465347

# Account protection
MINIMUM_ACCOUNT_AGE_DAYS = 7
VERY_NEW_ACCOUNT_HOURS = 24

# Data files
INVITE_DATA_FILE = "invite_data.json"
INVITE_RECORDS_FILE = "invite_records.json"


# ============================================================
# BOT SETUP
# ============================================================

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.invites = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# ============================================================
# DATA
# ============================================================

invite_data = {}
invite_records = {}
invite_cache = {}


# ============================================================
# JSON HELPERS
# ============================================================

def load_json(filename, default):
    try:
        if not os.path.exists(filename):
            return default

        with open(filename, "r", encoding="utf-8") as file:
            data = json.load(file)

        return data

    except Exception as e:
        print(f"[JSON ERROR] Could not load {filename}: {e}")
        return default


def save_json(filename, data):
    try:
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)

    except Exception as e:
        print(f"[JSON ERROR] Could not save {filename}: {e}")


def load_data():
    global invite_data
    global invite_records

    invite_data = load_json(INVITE_DATA_FILE, {})
    invite_records = load_json(INVITE_RECORDS_FILE, {})

    print("[DATA] Invite data loaded.")
    print("[DATA] Invite records loaded.")


def save_data():
    save_json(INVITE_DATA_FILE, invite_data)
    save_json(INVITE_RECORDS_FILE, invite_records)


# ============================================================
# INVITE DATA HELPERS
# ============================================================

def get_guild_data(guild_id):
    guild_id = str(guild_id)

    if guild_id not in invite_data:
        invite_data[guild_id] = {}

    return invite_data[guild_id]


def get_invite_count(guild_id, user_id):
    guild_data = get_guild_data(guild_id)

    return int(guild_data.get(str(user_id), 0))


def set_invite_count(guild_id, user_id, amount):
    guild_data = get_guild_data(guild_id)

    guild_data[str(user_id)] = max(0, int(amount))


def add_invite(guild_id, user_id):
    current = get_invite_count(guild_id, user_id)
    new_count = current + 1

    set_invite_count(guild_id, user_id, new_count)

    return new_count


def remove_invite(guild_id, user_id):
    current = get_invite_count(guild_id, user_id)
    new_count = max(0, current - 1)

    set_invite_count(guild_id, user_id, new_count)

    return new_count


# ============================================================
# ACCOUNT AGE
# ============================================================

def get_account_age(member):
    now = datetime.now(timezone.utc)

    created_at = member.created_at

    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    age = now - created_at

    return age


def get_account_age_days(member):
    age = get_account_age(member)

    return age.total_seconds() / 86400


def get_account_age_hours(member):
    age = get_account_age(member)

    return age.total_seconds() / 3600


def account_is_too_new(member):
    """
    Returns True if the account is younger than 7 days.
    """

    age_days = get_account_age_days(member)

    return age_days < MINIMUM_ACCOUNT_AGE_DAYS


def account_is_very_new(member):
    """
    Returns True if the account is younger than 24 hours.
    """

    age_hours = get_account_age_hours(member)

    return age_hours < VERY_NEW_ACCOUNT_HOURS


def account_age_text(member):
    age = get_account_age(member)

    total_seconds = int(age.total_seconds())

    if total_seconds < 0:
        return "Invalid account age"

    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60

    if days > 0:
        return f"{days} day(s), {hours} hour(s)"

    if hours > 0:
        return f"{hours} hour(s), {minutes} minute(s)"

    return f"{minutes} minute(s)"


# ============================================================
# PROGRESS BAR
# ============================================================

def make_progress_bar(current, target, length=10):
    if target <= 0:
        return "🟩" * length

    percentage = min(current / target, 1)

    filled = int(percentage * length)

    empty = length - filled

    return "🟩" * filled + "⬜" * empty


# ============================================================
# REWARD INFORMATION
# ============================================================

def get_next_reward(count):
    if count < 5:
        return 5, "$5 OFF"

    if count < 10:
        return 10, "$10 OFF"

    if count < 15:
        return 15, "FREE MEAL"

    return None, "All rewards unlocked!"


def reward_roles_for_count(count):
    roles = []

    if count >= 5:
        roles.append(FIVE_INVITE_ROLE)

    if count >= 10:
        roles.append(TEN_INVITE_ROLE)

    if count >= 15:
        roles.append(FIFTEEN_INVITE_ROLE)

    return roles


# ============================================================
# REWARD ROLE UPDATE
# ============================================================

async def update_reward_roles(member, old_count=None):
    if member is None:
        return

    guild = member.guild

    count = get_invite_count(guild.id, member.id)

    reward_role_ids = [
        FIVE_INVITE_ROLE,
        TEN_INVITE_ROLE,
        FIFTEEN_INVITE_ROLE
    ]

    desired_roles = reward_roles_for_count(count)

    print(
        f"[ROLES] Updating {member} | "
        f"Invites: {count} | "
        f"Desired roles: {desired_roles}"
    )

    for role_id in reward_role_ids:
        role = guild.get_role(role_id)

        if role is None:
            print(
                f"[ROLES] WARNING: Role {role_id} "
                f"was not found in {guild.name}"
            )
            continue

        should_have = role_id in desired_roles
        has_role = role in member.roles

        try:
            if should_have and not has_role:
                await member.add_roles(
                    role,
                    reason="Invite reward reached"
                )

                print(
                    f"[ROLES] Added {role.name} to {member}"
                )

            elif not should_have and has_role:
                await member.remove_roles(
                    role,
                    reason="Invite reward threshold no longer reached"
                )

                print(
                    f"[ROLES] Removed {role.name} from {member}"
                )

        except discord.Forbidden:
            print(
                f"[ROLES] FORBIDDEN: Could not modify "
                f"{role.name} for {member}"
            )

        except discord.HTTPException as e:
            print(
                f"[ROLES] HTTP ERROR modifying {role.name}: {e}"
            )


# ============================================================
# LOGGING
# ============================================================

async def send_invite_log(guild, embed):
    channel = guild.get_channel(INVITE_LOG_CHANNEL_ID)

    if channel is None:
        try:
            channel = await bot.fetch_channel(
                INVITE_LOG_CHANNEL_ID
            )
        except Exception as e:
            print(
                f"[LOG] Could not find invite log channel "
                f"{INVITE_LOG_CHANNEL_ID}: {e}"
            )
            return False

    try:
        await channel.send(embed=embed)

        print(
            f"[LOG] Sent invite log to #{channel.name}"
        )

        return True

    except discord.Forbidden:
        print(
            "[LOG] FORBIDDEN: Bot cannot send messages "
            "or embeds in the invite log channel."
        )

        return False

    except discord.HTTPException as e:
        print(f"[LOG] Discord error sending log: {e}")

        return False


# ============================================================
# CACHE INVITES
# ============================================================

async def cache_guild_invites(guild):
    try:
        invites = await guild.invites()

        invite_cache[guild.id] = {
            invite.code: {
                "uses": invite.uses or 0,
                "inviter_id": (
                    invite.inviter.id
                    if invite.inviter
                    else None
                )
            }
            for invite in invites
        }

        print(
            f"[INVITES] Cached {len(invites)} invites "
            f"for {guild.name}"
        )

    except discord.Forbidden:
        print(
            f"[INVITES] FORBIDDEN: Cannot view invites "
            f"for {guild.name}"
        )

    except discord.HTTPException as e:
        print(
            f"[INVITES] Could not cache invites "
            f"for {guild.name}: {e}"
        )

    except Exception as e:
        print(
            f"[INVITES] Unexpected cache error: {e}"
        )


# ============================================================
# FIND INVITER
# ============================================================

async def find_inviter(guild):
    try:
        current_invites = await guild.invites()

    except discord.Forbidden:
        print(
            f"[INVITES] FORBIDDEN: Bot cannot access "
            f"invites for {guild.name}"
        )

        return None, None

    except discord.HTTPException as e:
        print(
            f"[INVITES] HTTP error getting invites: {e}"
        )

        return None, None

    previous = invite_cache.get(guild.id, {})

    used_invite = None

    for invite in current_invites:
        old_data = previous.get(invite.code)

        old_uses = 0

        if old_data:
            old_uses = old_data.get("uses", 0)

        new_uses = invite.uses or 0

        if new_uses > old_uses:
            used_invite = invite
            break

    # Update cache immediately
    invite_cache[guild.id] = {
        invite.code: {
            "uses": invite.uses or 0,
            "inviter_id": (
                invite.inviter.id
                if invite.inviter
                else None
            )
        }
        for invite in current_invites
    }

    if used_invite is None:
        print(
            f"[INVITES] Could not determine which invite "
            f"was used in {guild.name}"
        )

        return None, None

    inviter = used_invite.inviter

    if inviter is None:
        print(
            f"[INVITES] Invite {used_invite.code} "
            f"has no inviter."
        )

        return None, used_invite

    print(
        f"[INVITES] Detected invite: "
        f"{used_invite.code} | "
        f"Inviter: {inviter} ({inviter.id})"
    )

    return inviter, used_invite


# ============================================================
# BOT READY
# ============================================================

@bot.event
async def on_ready():
    print("========================================")
    print("Invite Rewards Bot v2.0 ONLINE")
    print(f"Logged in as: {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print("========================================")

    load_data()

    # Sync slash commands
    try:
        synced = await bot.tree.sync()

        print(
            f"[COMMANDS] Synced {len(synced)} slash commands."
        )

    except Exception as e:
        print(
            f"[COMMANDS] Sync error: {e}"
        )

    # Cache invites
    for guild in bot.guilds:
        print(
            f"[STARTUP] Loading invites for {guild.name}"
        )

        await cache_guild_invites(guild)

    print("[STARTUP] Bot startup complete.")


# ============================================================
# MEMBER JOIN
# ============================================================

@bot.event
async def on_member_join(member):
    guild = member.guild

    print("========================================")
    print(f"[JOIN] {member} joined {guild.name}")
    print(f"[JOIN] User ID: {member.id}")
    print(
        f"[JOIN] Account created: "
        f"{member.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )
    print(
        f"[JOIN] Account age: "
        f"{account_age_text(member)}"
    )
    print("========================================")

    # --------------------------------------------------------
    # Find inviter
    # --------------------------------------------------------

    inviter, used_invite = await find_inviter(guild)

    inviter_id = inviter.id if inviter else None

    if inviter:
        print(
            f"[JOIN] Inviter detected: "
            f"{inviter} ({inviter.id})"
        )
    else:
        print("[JOIN] Inviter could not be detected.")

    # --------------------------------------------------------
    # Save record BEFORE doing anything else
    # --------------------------------------------------------

    guild_records = invite_records.setdefault(
        str(guild.id),
        {}
    )

    guild_records[str(member.id)] = {
        "inviter_id": inviter_id,
        "counted": False,
        "account_created": member.created_at.isoformat(),
        "joined_at": datetime.now(timezone.utc).isoformat()
    }

    # --------------------------------------------------------
    # ACCOUNT AGE PROTECTION
    # --------------------------------------------------------

    age_days = get_account_age_days(member)
    age_hours = get_account_age_hours(member)

    too_new = age_days < MINIMUM_ACCOUNT_AGE_DAYS
    very_new = age_hours < VERY_NEW_ACCOUNT_HOURS

    # --------------------------------------------------------
    # TOO NEW
    # --------------------------------------------------------

    if too_new:

        if very_new:
            status_title = "🚨 Extremely New Account"
            status_text = (
                "This account is less than 24 hours old.\n\n"
                "The invite was **NOT counted** toward rewards."
            )
        else:
            status_title = "⚠️ New Account Blocked"
            status_text = (
                f"This account is less than "
                f"{MINIMUM_ACCOUNT_AGE_DAYS} days old.\n\n"
                "The invite was **NOT counted** toward rewards."
            )

        embed = discord.Embed(
            title=status_title,
            description=status_text,
            color=discord.Color.red()
        )

        embed.add_field(
            name="👤 New Member",
            value=f"{member.mention}\n`{member.id}`",
            inline=False
        )

        embed.add_field(
            name="📅 Account Age",
            value=account_age_text(member),
            inline=True
        )

        embed.add_field(
            name="📆 Account Created",
            value=discord.utils.format_dt(
                member.created_at,
                style="F"
            ),
            inline=True
        )

        if inviter:
            embed.add_field(
                name="📨 Invited By",
                value=inviter.mention,
                inline=True
            )
        else:
            embed.add_field(
                name="📨 Invited By",
                value="Unknown",
                inline=True
            )

        embed.add_field(
            name="🛡️ Protection",
            value=(
                f"Minimum account age: "
                f"**{MINIMUM_ACCOUNT_AGE_DAYS} days**"
            ),
            inline=False
        )

        if inviter:
            embed.add_field(
                name="📊 Invite Count",
                value=(
                    f"{inviter.mention}: "
                    f"**{get_invite_count(guild.id, inviter.id)}** "
                    f"(unchanged)"
                ),
                inline=False
            )

        embed.set_footer(
            text="Invite Rewards Security"
        )

        await send_invite_log(guild, embed)

        save_data()

        print(
            f"[JOIN] ❌ NOT COUNTED — account is "
            f"{age_days:.2f} days old."
        )

        # Refresh cache
        await cache_guild_invites(guild)

        return

    # --------------------------------------------------------
    # VALID ACCOUNT
    # --------------------------------------------------------

    if inviter is None:

        embed = discord.Embed(
            title="📥 New Member Joined",
            description=(
                f"{member.mention} joined the server.\n\n"
                "The invite could not be identified, "
                "so no invite reward was given."
            ),
            color=discord.Color.orange()
        )

        embed.add_field(
            name="👤 Member",
            value=f"{member.mention}\n`{member.id}`",
            inline=False
        )

        embed.add_field(
            name="📅 Account Age",
            value=account_age_text(member),
            inline=True
        )

        embed.add_field(
            name="📨 Inviter",
            value="Unknown",
            inline=True
        )

        embed.set_footer(
            text="Invite Rewards System"
        )

        await send_invite_log(guild, embed)

        save_data()

        print(
            "[JOIN] ⚠️ Account passed age check, "
            "but inviter could not be identified."
        )

        await cache_guild_invites(guild)

        return

    # --------------------------------------------------------
    # COUNT VALID INVITE
    # --------------------------------------------------------

    old_count = get_invite_count(
        guild.id,
        inviter.id
    )

    new_count = add_invite(
        guild.id,
        inviter.id
    )

    guild_records[str(member.id)]["counted"] = True

    save_data()

    print(
        f"[JOIN] ✅ VALID INVITE COUNTED"
    )

    print(
        f"[JOIN] Inviter: {inviter} ({inviter.id})"
    )

    print(
        f"[JOIN] Count: {old_count} -> {new_count}"
    )

    # --------------------------------------------------------
    # Update reward roles
    # --------------------------------------------------------

    inviter_member = guild.get_member(inviter.id)

    if inviter_member:
        await update_reward_roles(
            inviter_member,
            old_count=old_count
        )
    else:
        print(
            f"[ROLES] Could not find inviter member "
            f"{inviter.id} in guild cache."
        )

    # --------------------------------------------------------
    # Reward notification
    # --------------------------------------------------------

    reward_message = "No new reward unlocked."

    if new_count == 5:
        reward_message = "🎉 **$5 OFF unlocked!**"

    elif new_count == 10:
        reward_message = "🎉 **$10 OFF unlocked!**"

    elif new_count == 15:
        reward_message = "🎉 **FREE MEAL unlocked!**"

    elif new_count > 15:
        reward_message = "⭐ All invite rewards remain unlocked."

    # --------------------------------------------------------
    # Log successful invite
    # --------------------------------------------------------

    embed = discord.Embed(
        title="🎉 Successful Invite",
        description=(
            f"{member.mention} joined using an invite from "
            f"{inviter.mention}."
        ),
        color=discord.Color.green()
    )

    embed.add_field(
        name="👤 New Member",
        value=f"{member.mention}\n`{member.id}`",
        inline=False
    )

    embed.add_field(
        name="📨 Invited By",
        value=inviter.mention,
        inline=True
    )

    embed.add_field(
        name="📅 Account Age",
        value=account_age_text(member),
        inline=True
    )

    embed.add_field(
        name="📊 Invite Count",
        value=f"**{old_count} → {new_count}**",
        inline=True
    )

    embed.add_field(
        name="🏆 Reward Status",
        value=reward_message,
        inline=False
    )

    embed.add_field(
        name="📈 Progress",
        value=(
            f"{make_progress_bar(new_count, 15)}\n"
            f"**{new_count}/15 successful invites**"
        ),
        inline=False
    )

    if used_invite:
        embed.add_field(
            name="🔗 Invite",
            value=f"`{used_invite.code}`",
            inline=True
        )

    embed.set_footer(
        text="Invite Rewards System"
    )

    await send_invite_log(guild, embed)

    # Refresh invite cache
    await cache_guild_invites(guild)


# ============================================================
# MEMBER LEAVE
# ============================================================

@bot.event
async def on_member_remove(member):
    guild = member.guild

    print("========================================")
    print(f"[LEAVE] {member} left {guild.name}")
    print("========================================")

    guild_records = invite_records.get(
        str(guild.id),
        {}
    )

    record = guild_records.get(
        str(member.id)
    )

    # --------------------------------------------------------
    # No record
    # --------------------------------------------------------

    if not record:
        print(
            f"[LEAVE] No invite record found for {member.id}"
        )

        embed = discord.Embed(
            title="📤 Member Left",
            description=(
                f"{member.mention} left the server.\n\n"
                "No invite record was found."
            ),
            color=discord.Color.orange()
        )

        embed.add_field(
            name="👤 Member",
            value=f"{member}\n`{member.id}`",
            inline=False
        )

        embed.set_footer(
            text="Invite Rewards System"
        )

        await send_invite_log(guild, embed)

        return

    inviter_id = record.get("inviter_id")
    counted = record.get("counted", False)

    # --------------------------------------------------------
    # Invite was not counted
    # --------------------------------------------------------

    if not counted or not inviter_id:
        print(
            "[LEAVE] Member's invite was not counted. "
            "No invite removed."
        )

        embed = discord.Embed(
            title="📤 Member Left",
            description=(
                f"{member.mention} left the server.\n\n"
                "Their invite was not counted, so no "
                "invite total was changed."
            ),
            color=discord.Color.orange()
        )

        embed.add_field(
            name="👤 Member",
            value=f"{member}\n`{member.id}`",
            inline=False
        )

        embed.add_field(
            name="📊 Invite Count",
            value="No change",
            inline=True
        )

        embed.set_footer(
            text="Invite Rewards System"
        )

        await send_invite_log(guild, embed)

        del guild_records[str(member.id)]

        save_data()

        return

    # --------------------------------------------------------
    # Remove counted invite
    # --------------------------------------------------------

    old_count = get_invite_count(
        guild.id,
        inviter_id
    )

    new_count = remove_invite(
        guild.id,
        inviter_id
    )

    print(
        f"[LEAVE] Removing invite from {inviter_id}: "
        f"{old_count} -> {new_count}"
    )

    inviter_member = guild.get_member(inviter_id)

    # Update roles if inviter is still in server
    if inviter_member:
        await update_reward_roles(
            inviter_member,
            old_count=old_count
        )

    # --------------------------------------------------------
    # Determine changed reward
    # --------------------------------------------------------

    role_change_text = "No reward role changed."

    if old_count >= 15 and new_count < 15:
        role_change_text = "❌ Free Meal role removed."

    elif old_count >= 10 and new_count < 10:
        role_change_text = "❌ $10 OFF role removed."

    elif old_count >= 5 and new_count < 5:
        role_change_text = "❌ $5 OFF role removed."

    # --------------------------------------------------------
    # Leave log
    # --------------------------------------------------------

    embed = discord.Embed(
        title="📤 Member Left",
        description=(
            f"{member.mention} left the server.\n\n"
            f"Their successful invite was removed from "
            f"{f'<@{inviter_id}>'}."
        ),
        color=discord.Color.red()
    )

    embed.add_field(
        name="👤 Member",
        value=f"{member}\n`{member.id}`",
        inline=False
    )

    embed.add_field(
        name="📨 Original Inviter",
        value=f"<@{inviter_id}>",
        inline=True
    )

    embed.add_field(
        name="📊 Invite Count",
        value=f"**{old_count} → {new_count}**",
        inline=True
    )

    embed.add_field(
        name="🏆 Reward Changes",
        value=role_change_text,
        inline=False
    )

    embed.add_field(
        name="📈 Current Progress",
        value=(
            f"{make_progress_bar(new_count, 15)}\n"
            f"**{new_count}/15 successful invites**"
        ),
        inline=False
    )

    embed.set_footer(
        text="Invite Rewards System"
    )

    await send_invite_log(guild, embed)

    # Remove member record
    del guild_records[str(member.id)]

    save_data()


# ============================================================
# /INVITES
# ============================================================

@bot.tree.command(
    name="invites",
    description="Check your successful invite count and rewards."
)
async def invites_command(interaction: discord.Interaction):

    guild = interaction.guild
    member = interaction.user

    count = get_invite_count(
        guild.id,
        member.id
    )

    next_target, next_reward = get_next_reward(count)

    embed = discord.Embed(
        title="📨 Your Invite Rewards",
        description=(
            "Invite people to the server and earn rewards!"
        ),
        color=discord.Color.blurple()
    )

    embed.set_author(
        name=member.display_name,
        icon_url=member.display_avatar.url
    )

    embed.add_field(
        name="📊 Successful Invites",
        value=f"**{count}**",
        inline=True
    )

    if next_target:
        remaining = next_target - count

        embed.add_field(
            name="🎯 Next Reward",
            value=(
                f"**{next_reward}**\n"
                f"{remaining} more invite(s)"
            ),
            inline=True
        )

        embed.add_field(
            name="📈 Progress",
            value=(
                f"{make_progress_bar(count, next_target)}\n"
                f"**{count}/{next_target}**"
            ),
            inline=False
        )

    else:
        embed.add_field(
            name="🏆 Status",
            value="**All rewards unlocked!**",
            inline=False
        )

    embed.add_field(
        name="🎁 Reward Levels",
        value=(
            "👥 **5 invites** → $5 OFF\n"
            "👥 **10 invites** → $10 OFF\n"
            "👥 **15 invites** → FREE MEAL"
        ),
        inline=False
    )

    embed.add_field(
        name="🛡️ Invite Protection",
        value=(
            f"Accounts younger than "
            f"**{MINIMUM_ACCOUNT_AGE_DAYS} days** "
            "do not count."
        ),
        inline=False
    )

    embed.set_footer(
        text="Invite Rewards System"
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# ============================================================
# /REWARDS
# ============================================================

@bot.tree.command(
    name="rewards",
    description="Show the server invite reward information."
)
async def rewards_command(interaction: discord.Interaction):

    member = interaction.user

    staff_role = interaction.guild.get_role(
        REWARDS_ADMIN_ROLE_ID
    )

    if staff_role is None:
        await interaction.response.send_message(
            "❌ The staff role could not be found.",
            ephemeral=True
        )
        return

    if staff_role not in member.roles:
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🎁 Invite Rewards Program",
        description=(
            "Bring real members into the server and earn "
            "rewards based on your successful invites.\n\n"
            "The system automatically tracks which invite was "
            "used and updates your reward roles."
        ),
        color=discord.Color.gold()
    )

    embed.add_field(
        name="🥉 5 Successful Invites",
        value=(
            "Reward Role\n"
            "💵 **$5 OFF**"
        ),
        inline=False
    )

    embed.add_field(
        name="🥈 10 Successful Invites",
        value=(
            "Reward Role\n"
            "💵 **$10 OFF**"
        ),
        inline=False
    )

    embed.add_field(
        name="🥇 15 Successful Invites",
        value=(
            "Reward Role\n"
            "🍽️ **FREE MEAL**"
        ),
        inline=False
    )

    embed.add_field(
        name="🛡️ Account Protection",
        value=(
            f"Accounts younger than "
            f"**{MINIMUM_ACCOUNT_AGE_DAYS} days** "
            "will not count toward invite rewards.\n\n"
            f"Accounts under **{VERY_NEW_ACCOUNT_HOURS} hours** "
            "are flagged as extremely new."
        ),
        inline=False
    )

    embed.add_field(
        name="📤 If Someone Leaves",
        value=(
            "If a counted member leaves the server, their "
            "invite is automatically removed from the inviter's "
            "total.\n\n"
            "Reward roles are updated automatically."
        ),
        inline=False
    )

    embed.add_field(
        name="📊 Check Your Invites",
        value=(
            "Use `/invites` to see your current count, "
            "progress, and next reward."
        ),
        inline=False
    )

    embed.set_footer(
        text="Invite Rewards System"
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# /HELP
# ============================================================

@bot.tree.command(
    name="help",
    description="Learn how the invite reward system works."
)
async def help_command(interaction: discord.Interaction):

    embed = discord.Embed(
        title="❓ Invite Rewards Help",
        description=(
            "Here's how the invite system works."
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="1️⃣ Invite Someone",
        value=(
            "Create an invite and have someone join "
            "the server."
        ),
        inline=False
    )

    embed.add_field(
        name="2️⃣ Account Check",
        value=(
            f"The account must be at least "
            f"**{MINIMUM_ACCOUNT_AGE_DAYS} days old** "
            "for the invite to count."
        ),
        inline=False
    )

    embed.add_field(
        name="3️⃣ Get Credit",
        value=(
            "If the account passes the protection check, "
            "the inviter gets +1 successful invite."
        ),
        inline=False
    )

    embed.add_field(
        name="4️⃣ Earn Rewards",
        value=(
            "5 invites → **$5 OFF**\n"
            "10 invites → **$10 OFF**\n"
            "15 invites → **FREE MEAL**"
        ),
        inline=False
    )

    embed.add_field(
        name="5️⃣ Member Leaves",
        value=(
            "If that member leaves, their counted invite "
            "is removed automatically."
        ),
        inline=False
    )

    embed.add_field(
        name="📊 Check Progress",
        value=(
            "Use `/invites` at any time."
        ),
        inline=False
    )

    embed.set_footer(
        text="Invite Rewards System"
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# ============================================================
# COMMAND ERROR HANDLER
# ============================================================

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error
):

    print(
        f"[COMMAND ERROR] {error}"
    )

    try:
        if interaction.response.is_done():
            await interaction.followup.send(
                "❌ Something went wrong while running that command.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ Something went wrong while running that command.",
                ephemeral=True
            )

    except Exception as e:
        print(
            f"[COMMAND ERROR] Could not send error message: {e}"
        )


# ============================================================
# START BOT
# ============================================================

if not TOKEN:
    print("========================================")
    print("ERROR: DISCORD_TOKEN IS NOT SET")
    print("========================================")
    raise RuntimeError(
        "DISCORD_TOKEN environment variable is not set."
    )


print("[START] Starting Discord bot...")

bot.run(TOKEN)
