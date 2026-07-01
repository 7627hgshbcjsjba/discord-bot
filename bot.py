import discord
from discord.ext import commands
import asyncio
from datetime import timedelta
from discord.ext.commands import (
    CheckFailure,
    MissingPermissions,
    MissingRequiredArgument,
    BadArgument,
)
import os
import json
import time
import io

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)

TARGET_ROLE_ID = 1521658712626823290

# --------------------
# STATUS TRACKER CONFIG
# --------------------
STATUS_USER_ID = 1498086936781262899
STATUS_CHANNEL_ID = 1521693219652370532

STATUS_NAMES = {
    "online": "🟢▫️online▫️𝖕𝖚𝖑𝖑𝖊",
    "idle": "🟡▫️idle▫️𝖕𝖚𝖑𝖑𝖊",
    "dnd": "🔴▫️dnd▫️𝖕𝖚𝖑𝖑𝖊",
    "offline": "🔴▫️offline▫️𝖕𝖚𝖑𝖑𝖊",
}

LAST_RENAME = {}
LAST_STATUS = {}


# ============== PERSISTENT WARNS ==============
WARNS_FILE = "warns.json"

def load_warns():
    if os.path.exists(WARNS_FILE):
        try:
            with open(WARNS_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_warns():
    with open(WARNS_FILE, "w") as f:
        json.dump(warn_storage, f, indent=2)

warn_storage = load_warns()
# ==============================================


# ============== PERSISTENT BOT ACCESS ==============
BOT_ACCESS_FILE = "bot_access.json"

def load_bot_access():
    if os.path.exists(BOT_ACCESS_FILE):
        try:
            with open(BOT_ACCESS_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_bot_access():
    with open(BOT_ACCESS_FILE, "w") as f:
        json.dump(bot_allowed_users, f, indent=2)

bot_allowed_users = load_bot_access()
# ====================================================


@bot.check
async def is_admin_or_owner(ctx):
    if ctx.author.id == ctx.guild.owner_id:
        return True
    if ctx.author.guild_permissions.administrator:
        return True
    if str(ctx.author.id) in bot_allowed_users:
        return True
    return False


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await _set_initial_status()


@bot.event
async def on_presence_update(before, after):
    if after.id != STATUS_USER_ID:
        return
    if before.status == after.status:
        return
    await _update_status_channel(after)


@bot.event
async def on_member_update(before, after):
    if after.id != STATUS_USER_ID:
        return
    if before.status == after.status:
        return
    await _update_status_channel(after)


async def _update_status_channel(member):
    guild = member.guild
    channel = guild.get_channel(STATUS_CHANNEL_ID)
    if channel is None:
        return

    status_key = str(member.status)
    new_name = STATUS_NAMES.get(status_key, STATUS_NAMES["offline"])

    if channel.name == new_name:
        return
    if LAST_STATUS.get(channel.id) == status_key:
        return

    now = time.time()
    last = LAST_RENAME.get(channel.id, 0)
    if now - last < 120:
        return

    LAST_RENAME[channel.id] = now
    LAST_STATUS[channel.id] = status_key

    try:
        await channel.edit(name=new_name, reason=f"Status changed to {status_key}")
        print(f"✅ Status channel renamed to: {new_name}")
    except discord.Forbidden:
        print(f"❌ I don't have permission to edit channel {channel.name}")
    except discord.HTTPException as e:
        print(f"❌ Failed to rename channel: {e}")


async def _set_initial_status():
    if not bot.guilds:
        return
    guild = bot.guilds[0]
    member = guild.get_member(STATUS_USER_ID)
    if member is None:
        print(f"⚠️ Could not find user with ID {STATUS_USER_ID}")
        return
    await _update_status_channel(member)


@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name="general")
    if channel is None:
        channel = member.guild.system_channel
    if channel is not None:
        try:
            await channel.send(
                f"👋 Welcome to **{member.guild.name}**, {member.mention}! "
                f"Please read the rules with `!rules` and have fun!"
            )
        except discord.Forbidden:
            pass


@bot.command()
async def modhelp(ctx):
    embed = discord.Embed(
        title="🛡️ Moderation Bot Help",
        description="List of available commands:",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="Moderation",
        value="""
!warn @user reason
!warnings @user
!warncount @user
!topwarns
!clearwarns @user
!mute @user minutes reason
!unmute @user
!kick @user reason
!ban @user reason
!unban user_id
!purge amount
""",
        inline=False,
    )
    embed.add_field(
        name="Channel Control",
        value="""
!lock
!unlock
!quicklock
!quickunlock
!private
!public
!secure
!unsecure
!mediaenable
!mediadisable
!givechannelaccess @user
!ungivechannelaccess @user
!readhistoryall
!readhistoryhere
!slowmode seconds/off
""",
        inline=False,
    )
    embed.add_field(
        name="Roles",
        value="""
!role add @user @role1 @role2 ...
!role remove @user @role1 @role2 ...
!role list @user
""",
        inline=False,
    )
    embed.add_field(
        name="Messaging",
        value="""
!say <message>
!say embed <title> | <message>
!pingeveryone [message]
""",
        inline=False,
    )
    embed.add_field(
        name="Bot Access",
        value="""
!givebotaccess @user
!ungivebotaccess @user
!botaccesslist
""",
        inline=False,
    )
    embed.add_field(
        name="Backup",
        value="""
!exportwarns
!importwarns
!exportaccess
!importaccess
!fullbackup
""",
        inline=False,
    )
    embed.add_field(
        name="Info",
        value="""
!ping
!rules
!rule number
!commands
!modhelp
""",
        inline=False,
    )
    await ctx.send(embed=embed)


@bot.command()
async def commands(ctx):
    await ctx.send(
        "Commands: !warn !warnings !warncount !topwarns !clearwarns "
        "!mute !unmute !kick !ban !unban !purge "
        "!lock !unlock !quicklock !quickunlock !private !public "
        "!secure !unsecure !mediaenable !mediadisable "
        "!givechannelaccess !ungivechannelaccess "
        "!givebotaccess !ungivebotaccess !botaccesslist "
        "!exportwarns !importwarns !exportaccess !importaccess !fullbackup "
        "!readhistoryall !readhistoryhere !slowmode "
        "!role add !role remove !role list "
        "!say !pingeveryone "
        "!ping !rules !rule !commands !modhelp"
    )


@bot.command()
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! {latency}ms")


@bot.command()
async def rules(ctx):
    embed = discord.Embed(
        title="📜 Server Rules",
        description=(
            "Welcome! This is a **chill hangout server**, so just be respectful, "
            "have fun, and follow the rules below. 👇"
        ),
        color=discord.Color.purple()
    )
    embed.add_field(name="1️⃣ Be Respectful", value="Treat everyone with kindness. No harassment, hate speech, or bullying.", inline=False)
    embed.add_field(name="2️⃣ No Spam or Flooding", value="Don't spam messages, emojis, mentions, or caps. Keep chats clean.", inline=False)
    embed.add_field(name="3️⃣ No NSFW or Inappropriate Content", value="Keep it SFW. No nudity, gore, or shocking content — this is a chill space.", inline=False)
    embed.add_field(name="4️⃣ No Advertising", value="Don't promote other servers, discords, or self-promote without permission.", inline=False)
    embed.add_field(name="5️⃣ Use the Right Channels", value="Keep conversations on topic. Use the correct channels for what you're posting.", inline=False)
    embed.add_field(name="6️⃣ Listen to Staff", value="Follow instructions from moderators and admins. If you disagree, DM an admin calmly.", inline=False)
    embed.add_field(name="7️⃣ No Impersonation", value="Don't pretend to be someone else, including staff or other members.", inline=False)
    embed.add_field(name="8️⃣ Have Fun & Be Chill 😎", value="Hang out, chat, play games, share memes — just be a good person and enjoy the server!", inline=False)
    embed.set_footer(text="Breaking these rules may result in a warn, mute, kick, or ban.")
    if ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url)
    await ctx.send(embed=embed)


@bot.command()
async def rule(ctx, number: int):
    rules_list = {
        1: "1️⃣ Be Respectful — Treat everyone with kindness. No harassment, hate speech, or bullying.",
        2: "2️⃣ No Spam or Flooding — Don't spam messages, emojis, mentions, or caps.",
        3: "3️⃣ No NSFW or Inappropriate Content — Keep it SFW.",
        4: "4️⃣ No Advertising — Don't promote other servers or self-promote.",
        5: "5️⃣ Use the Right Channels — Keep conversations on topic.",
        6: "6️⃣ Listen to Staff — Follow instructions from moderators and admins.",
        7: "7️⃣ No Impersonation — Don't pretend to be someone else.",
        8: "8️⃣ Have Fun & Be Chill 😎 — Just be a good person and enjoy the server!",
    }
    if number not in rules_list:
        await ctx.send("❌ That rule doesn't exist. Try `!rules` to see them all.")
        return
    await ctx.send(rules_list[number])


@bot.command()
async def warn(ctx, member: discord.Member, *, reason="No reason provided"):
    user_id = str(member.id)
    if user_id not in warn_storage:
        warn_storage[user_id] = []
    warn_storage[user_id].append(reason)
    save_warns()

    embed = discord.Embed(
        title="⚠️ Member Warned",
        color=discord.Color.orange(),
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="User", value=member.mention, inline=True)
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name="Total Warnings", value=str(len(warn_storage[user_id])), inline=True)
    embed.set_footer(text=f"User ID: {member.id}")
    await ctx.send(embed=embed)


@bot.command()
async def warnings(ctx, member: discord.Member):
    user_id = str(member.id)
    if user_id not in warn_storage or len(warn_storage[user_id]) == 0:
        await ctx.send(f"✅ {member.mention} has no warnings.")
        return
    warn_list = "\n".join([f"{i+1}. {r}" for i, r in enumerate(warn_storage[user_id])])
    await ctx.send(f"⚠️ Warnings for {member.mention}:\n{warn_list}")


@bot.command()
async def warncount(ctx, member: discord.Member):
    user_id = str(member.id)
    if user_id not in warn_storage or len(warn_storage[user_id]) == 0:
        await ctx.send(f"✅ {member.mention} has **0** warnings.")
        return
    count = len(warn_storage[user_id])
    await ctx.send(f"📊 {member.mention} has **{count}** warning(s).")


@bot.command()
async def topwarns(ctx):
    if not warn_storage:
        await ctx.send("✅ Nobody has any warnings in this server.")
        return
    sorted_users = sorted(warn_storage.items(), key=lambda item: len(item[1]), reverse=True)
    lines = []
    for i, (user_id, reasons) in enumerate(sorted_users[:10], start=1):
        member = ctx.guild.get_member(int(user_id))
        name = member.mention if member else f"`<{user_id}>`"
        lines.append(f"**{i}.** {name} — {len(reasons)} warning(s)")
    embed = discord.Embed(title="🏆 Top Warned Members", description="\n".join(lines), color=discord.Color.orange())
    await ctx.send(embed=embed)


@bot.command()
async def clearwarns(ctx, member: discord.Member):
    user_id = str(member.id)
    warn_storage[user_id] = []
    save_warns()
    embed = discord.Embed(
        title="🧹 Warnings Cleared",
        description=f"All warnings for {member.mention} have been cleared.",
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
    embed.set_footer(text=f"User ID: {member.id}")
    await ctx.send(embed=embed)


# ============== BACKUP COMMANDS ==============
@bot.command()
async def exportwarns(ctx):
    """Export all warns as a JSON file you can download."""
    if not warn_storage:
        await ctx.send("✅ No warns to export.")
        return

    data = json.dumps(warn_storage, indent=2)
    file = discord.File(io.BytesIO(data.encode()), filename=f"warns_backup_{int(time.time())}.json")

    embed = discord.Embed(
        title="📥 Warns Backup",
        description=(
            f"Here's your warns backup file.\n\n"
            f"• **Total users with warns:** {len(warn_storage)}\n"
            f"• **Total warnings:** {sum(len(v) for v in warn_storage.values())}\n\n"
            f"💡 Save this file! Use `!importwarns` (attach the file) to restore warns on a new bot instance."
        ),
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow()
    )
    await ctx.send(embed=embed, file=file)


@bot.command()
async def importwarns(ctx):
    """Import warns from a JSON file. Attach the file to your message."""
    if not ctx.message.attachments:
        await ctx.send("❌ Please attach a JSON file to import!\n\n**Usage:** Attach the backup file and type `!importwarns`")
        return

    attachment = ctx.message.attachments[0]

    if not attachment.filename.endswith(".json"):
        await ctx.send("❌ File must be a `.json` file!")
        return

    try:
        data = json.loads(await attachment.read())

        if not isinstance(data, dict):
            await ctx.send("❌ Invalid file format! Expected a JSON object.")
            return

        # Merge with existing warns (add to existing, don't overwrite)
        imported_count = 0
        for user_id, reasons in data.items():
            if user_id not in warn_storage:
                warn_storage[user_id] = []
            if isinstance(reasons, list):
                for reason in reasons:
                    if reason not in warn_storage[user_id]:
                        warn_storage[user_id].append(reason)
                        imported_count += 1

        save_warns()

        embed = discord.Embed(
            title="✅ Warns Imported",
            description=(
                f"Successfully imported warns!\n\n"
                f"• **Users affected:** {len(data)}\n"
                f"• **New warnings added:** {imported_count}\n"
                f"• **Total warns now:** {sum(len(v) for v in warn_storage.values())}"
            ),
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=f"Imported by {ctx.author.display_name}")
        await ctx.send(embed=embed)

    except json.JSONDecodeError:
        await ctx.send("❌ Invalid JSON file! Make sure it's a valid backup.")
    except Exception as e:
        await ctx.send(f"❌ Failed to import: {e}")


@bot.command()
async def exportaccess(ctx):
    """Export bot access list as a JSON file."""
    if not bot_allowed_users:
        await ctx.send("✅ No bot access entries to export.")
        return

    data = json.dumps(bot_allowed_users, indent=2)
    file = discord.File(io.BytesIO(data.encode()), filename=f"bot_access_backup_{int(time.time())}.json")

    embed = discord.Embed(
        title="📥 Bot Access Backup",
        description=(
            f"Here's your bot access backup.\n\n"
            f"• **Total users with access:** {len(bot_allowed_users)}\n\n"
            f"💡 Save this file! Use `!importaccess` (attach the file) to restore on a new bot instance."
        ),
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow()
    )
    await ctx.send(embed=embed, file=file)


@bot.command()
async def importaccess(ctx):
    """Import bot access list from a JSON file. Attach the file to your message."""
    if not ctx.message.attachments:
        await ctx.send("❌ Please attach a JSON file to import!\n\n**Usage:** Attach the backup file and type `!importaccess`")
        return

    attachment = ctx.message.attachments[0]

    if not attachment.filename.endswith(".json"):
        await ctx.send("❌ File must be a `.json` file!")
        return

    try:
        data = json.loads(await attachment.read())

        if not isinstance(data, list):
            await ctx.send("❌ Invalid file format! Expected a JSON list of user IDs.")
            return

        added = 0
        for user_id in data:
            user_id = str(user_id)
            if user_id not in bot_allowed_users:
                bot_allowed_users.append(user_id)
                added += 1

        save_bot_access()

        embed = discord.Embed(
            title="✅ Bot Access Imported",
            description=(
                f"Successfully imported bot access!\n\n"
                f"• **New users added:** {added}\n"
                f"• **Total users with access:** {len(bot_allowed_users)}"
            ),
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=f"Imported by {ctx.author.display_name}")
        await ctx.send(embed=embed)

    except json.JSONDecodeError:
        await ctx.send("❌ Invalid JSON file! Make sure it's a valid backup.")
    except Exception as e:
        await ctx.send(f"❌ Failed to import: {e}")


@bot.command()
async def fullbackup(ctx):
    """Download both warns and bot access in one file."""
    backup_data = {
        "warns": warn_storage,
        "bot_access": bot_allowed_users,
        "backup_date": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    data = json.dumps(backup_data, indent=2)
    file = discord.File(io.BytesIO(data.encode()), filename=f"full_backup_{int(time.time())}.json")

    embed = discord.Embed(
        title="📦 Full Backup",
        description=(
            f"Here's a complete backup of all bot data.\n\n"
            f"• **Users with warns:** {len(warn_storage)}\n"
            f"• **Total warnings:** {sum(len(v) for v in warn_storage.values())}\n"
            f"• **Users with bot access:** {len(bot_allowed_users)}\n\n"
            f"💡 Use `!importwarns` and `!importaccess` separately to restore."
        ),
        color=discord.Color.purple(),
        timestamp=discord.utils.utcnow()
    )
    await ctx.send(embed=embed, file=file)


@importwarns.error
async def importwarns_error(ctx, error):
    print(f"Ignored exception in command importwarns: {error}")


@importaccess.error
async def importaccess_error(ctx, error):
    print(f"Ignored exception in command importaccess: {error}")
# ==========================================


@bot.command()
async def mute(ctx, member: discord.Member, minutes: int, *, reason="No reason provided"):
    if minutes <= 0:
        await ctx.send("❌ Mute duration must be greater than 0 minutes.")
        return
    if minutes > 40320:
        await ctx.send("❌ Maximum mute duration is 28 days (40320 minutes).")
        return
    duration = discord.utils.utcnow() + timedelta(minutes=minutes)
    await member.timeout(duration, reason=reason)
    embed = discord.Embed(title="🔇 Member Muted", color=discord.Color.red(), timestamp=discord.utils.utcnow())
    embed.add_field(name="User", value=member.mention, inline=True)
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
    embed.add_field(name="Duration", value=f"{minutes} minute(s)", inline=True)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.set_footer(text=f"User ID: {member.id}")
    await ctx.send(embed=embed)


@bot.command()
async def unmute(ctx, member: discord.Member):
    await member.timeout(None)
    embed = discord.Embed(title="🔊 Member Unmuted", color=discord.Color.green(), timestamp=discord.utils.utcnow())
    embed.add_field(name="User", value=member.mention, inline=True)
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
    embed.set_footer(text=f"User ID: {member.id}")
    await ctx.send(embed=embed)


@bot.command()
async def kick(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.kick(reason=reason)
    embed = discord.Embed(title="👢 Member Kicked", color=discord.Color.dark_orange(), timestamp=discord.utils.utcnow())
    embed.add_field(name="User", value=str(member), inline=True)
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.set_footer(text=f"User ID: {member.id}")
    await ctx.send(embed=embed)


@bot.command()
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.ban(reason=reason)
    embed = discord.Embed(title="🔨 Member Banned", color=discord.Color.dark_red(), timestamp=discord.utils.utcnow())
    embed.add_field(name="User", value=str(member), inline=True)
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.set_footer(text=f"User ID: {member.id}")
    await ctx.send(embed=embed)


@bot.command()
async def unban(ctx, user_id: int):
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user)
    embed = discord.Embed(title="♻️ Member Unbanned", color=discord.Color.green(), timestamp=discord.utils.utcnow())
    embed.add_field(name="User", value=str(user), inline=True)
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
    embed.set_footer(text=f"User ID: {user.id}")
    await ctx.send(embed=embed)


@bot.command()
async def purge(ctx, amount: int):
    if amount < 1:
        await ctx.send("❌ Must be greater than 0.")
        return
    deleted = await ctx.channel.purge(limit=amount + 1)
    count = len(deleted) - 1
    embed = discord.Embed(
        title="🧹 Messages Purged",
        description=f"Deleted **{count}** message(s) in {ctx.channel.mention}.",
        color=discord.Color.greyple(),
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
    embed.set_footer(text=f"Channel ID: {ctx.channel.id}")
    msg = await ctx.send(embed=embed)
    await msg.delete(delay=5)


@bot.command()
async def lock(ctx):
    guild = ctx.guild
    channel = ctx.channel
    locked_roles = []
    for role in guild.roles:
        if role.is_default():
            continue
        if role.permissions.administrator:
            continue
        overwrite = channel.overwrites_for(role)
        if overwrite.send_messages is False:
            continue
        try:
            await channel.set_permissions(role, send_messages=False, add_reactions=False, speak=False, connect=False)
            locked_roles.append(role.name)
        except discord.Forbidden:
            pass
    embed = discord.Embed(title="🔒 Channel Locked", description=f"{channel.mention} has been locked.", color=discord.Color.red(), timestamp=discord.utils.utcnow())
    embed.add_field(name="Roles Affected", value=str(len(locked_roles)), inline=True)
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
    embed.set_footer(text="Admins can still talk.")
    await ctx.send(embed=embed)


@bot.command()
async def unlock(ctx):
    guild = ctx.guild
    channel = ctx.channel
    unlocked_roles = []
    for role in guild.roles:
        if role.is_default():
            continue
        if role.permissions.administrator:
            continue
        overwrite = channel.overwrites_for(role)
        if overwrite.send_messages is False:
            try:
                await channel.set_permissions(role, overwrite=None)
                unlocked_roles.append(role.name)
            except discord.Forbidden:
                pass
    embed = discord.Embed(title="🔓 Channel Unlocked", description=f"{channel.mention} has been unlocked.", color=discord.Color.green(), timestamp=discord.utils.utcnow())
    embed.add_field(name="Roles Restored", value=str(len(unlocked_roles)), inline=True)
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
    await ctx.send(embed=embed)


@bot.command()
async def quicklock(ctx):
    role = ctx.guild.get_role(TARGET_ROLE_ID)
    if role is None:
        await ctx.send(f"❌ Role with ID `{TARGET_ROLE_ID}` not found.")
        return
    try:
        await ctx.channel.set_permissions(role, overwrite=None)
        overwrite = discord.PermissionOverwrite(
            view_channel=True, send_messages=False, add_reactions=False,
            attach_files=False, embed_links=False, speak=False, connect=False,
        )
        await ctx.channel.set_permissions(role, overwrite=overwrite)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to edit this channel's permissions. Make sure my role is above the Member role.")
        return
    embed = discord.Embed(
        title="🔒 Quick Lock Applied",
        description=f"Channel {ctx.channel.mention} has been locked for the **{role.name}** role.\nThey can view the channel but cannot send messages, files, embeds, or reactions.",
        color=discord.Color.red(), timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="Locked Role", value=role.mention, inline=True)
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
    await ctx.send(embed=embed)


@bot.command()
async def quickunlock(ctx):
    role = ctx.guild.get_role(TARGET_ROLE_ID)
    if role is None:
        await ctx.send(f"❌ Role with ID `{TARGET_ROLE_ID}` not found.")
        return
    try:
        await ctx.channel.set_permissions(role, overwrite=None)
        overwrite = discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True,
            add_reactions=True, attach_files=True, embed_links=True, connect=True, speak=True,
        )
        await ctx.channel.set_permissions(role, overwrite=overwrite)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to edit this channel's permissions. Make sure my role is above the Member role.")
        return
    embed = discord.Embed(
        title="🔓 Quick Unlock Applied",
        description=f"Channel {ctx.channel.mention} has been unlocked and the **{role.name}** role has been re-added with full access.",
        color=discord.Color.green(), timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="Restored Role", value=role.mention, inline=True)
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
    await ctx.send(embed=embed)


@bot.command()
async def mediaenable(ctx):
    role = ctx.guild.get_role(TARGET_ROLE_ID)
    if role is None:
        await ctx.send(f"❌ Role with ID `{TARGET_ROLE_ID}` not found.")
        return
    try:
        await ctx.channel.set_permissions(role, overwrite=None)
        overwrite = discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True,
            add_reactions=True, attach_files=True, embed_links=True, connect=True, speak=True,
        )
        await ctx.channel.set_permissions(role, overwrite=overwrite)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to edit this channel's permissions. Make sure my role is above the Member role.")
        return
    embed = discord.Embed(
        title="🖼️ Media Access Enabled",
        description=f"**{role.name}** can now send files, photos, and embeds in {ctx.channel.mention}.",
        color=discord.Color.green(), timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="Updated Role", value=role.mention, inline=True)
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
    await ctx.send(embed=embed)


@bot.command()
async def mediadisable(ctx):
    role = ctx.guild.get_role(TARGET_ROLE_ID)
    if role is None:
        await ctx.send(f"❌ Role with ID `{TARGET_ROLE_ID}` not found.")
        return
    try:
        await ctx.channel.set_permissions(role, overwrite=None)
        overwrite = discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True,
            add_reactions=True, attach_files=False, embed_links=False, connect=True, speak=True,
        )
        await ctx.channel.set_permissions(role, overwrite=overwrite)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to edit this channel's permissions. Make sure my role is above the Member role.")
        return
    embed = discord.Embed(
        title="🚫 Media Access Disabled",
        description=f"**{role.name}** can no longer send files, photos, or embeds in {ctx.channel.mention}.\nThey can still send text messages and react.",
        color=discord.Color.orange(), timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="Updated Role", value=role.mention, inline=True)
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
    await ctx.send(embed=embed)


@bot.command()
async def givechannelaccess(ctx, member: discord.Member):
    """Give a member access to send messages, files, and embeds in the current channel."""
    guild = ctx.guild
    channel = ctx.channel
    target = member

    bot_perms = channel.permissions_for(guild.me)
    if not bot_perms.manage_channels:
        await ctx.send("❌ I don't have permission to edit this channel's permissions. "
                       "Make sure my role has **Manage Channels** enabled.")
        return

    if target.top_role >= guild.me.top_role:
        await ctx.send(f"❌ I can't edit permissions for {target.mention} — their role is higher than or equal to mine.")
        return

    try:
        overwrite = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True,
            add_reactions=True,
            connect=True,
            speak=True,
        )
        await channel.set_permissions(target, overwrite=overwrite)

        embed = discord.Embed(
            title="✅ Channel Access Granted",
            description=(
                f"{target.mention} now has access to {channel.mention}.\n\n"
                f"They can:\n"
                f"• ✅ View the channel\n"
                f"• ✅ Send messages\n"
                f"• ✅ Send files and photos\n"
                f"• ✅ Post embeds\n"
                f"• ✅ Add reactions\n"
                f"• ✅ Read message history"
            ),
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Granted By", value=ctx.author.mention, inline=True)
        embed.add_field(name="User ID", value=str(target.id), inline=True)
        embed.set_thumbnail(url=target.display_avatar.url)
        await ctx.send(embed=embed)

    except discord.Forbidden:
        await ctx.send(f"❌ I don't have permission to edit permissions for {target.mention}.")
    except discord.HTTPException as e:
        await ctx.send(f"❌ Failed to set permissions: {e}")


@bot.command()
async def ungivechannelaccess(ctx, member: discord.Member):
    """Remove a member's custom access permissions from the current channel."""
    guild = ctx.guild
    channel = ctx.channel
    target = member

    bot_perms = channel.permissions_for(guild.me)
    if not bot_perms.manage_channels:
        await ctx.send("❌ I don't have permission to edit this channel's permissions. "
                       "Make sure my role has **Manage Channels** enabled.")
        return

    if target.top_role >= guild.me.top_role:
        await ctx.send(f"❌ I can't edit permissions for {target.mention} — their role is higher than or equal to mine.")
        return

    current_overwrite = channel.overwrites_for(target)
    if current_overwrite.is_empty():
        await ctx.send(f"⚠️ {target.mention} doesn't have any custom permissions in {channel.mention}.")
        return

    try:
        await channel.set_permissions(target, overwrite=None)

        embed = discord.Embed(
            title="🚫 Channel Access Removed",
            description=(
                f"{target.mention} no longer has custom access to {channel.mention}.\n\n"
                f"• ❌ Custom permission overrides have been cleared\n"
                f"• Their access now follows their **role permissions**"
            ),
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Removed By", value=ctx.author.mention, inline=True)
        embed.add_field(name="User ID", value=str(target.id), inline=True)
        embed.set_thumbnail(url=target.display_avatar.url)
        await ctx.send(embed=embed)

    except discord.Forbidden:
        await ctx.send(f"❌ I don't have permission to edit permissions for {target.mention}.")
    except discord.HTTPException as e:
        await ctx.send(f"❌ Failed to remove permissions: {e}")


@givechannelaccess.error
async def givechannelaccess_error(ctx, error):
    if isinstance(error, MissingRequiredArgument):
        await ctx.send("❌ Usage: `!givechannelaccess @user`")
    else:
        print(f"Ignored exception in command givechannelaccess: {error}")


@ungivechannelaccess.error
async def ungivechannelaccess_error(ctx, error):
    if isinstance(error, MissingRequiredArgument):
        await ctx.send("❌ Usage: `!ungivechannelaccess @user`")
    else:
        print(f"Ignored exception in command ungivechannelaccess: {error}")


@bot.command()
async def givebotaccess(ctx, member: discord.Member):
    """Allow a member to use bot commands even without admin permissions."""
    target_id = str(member.id)

    if target_id in bot_allowed_users:
        await ctx.send(f"⚠️ {member.mention} already has bot access.")
        return

    bot_allowed_users.append(target_id)
    save_bot_access()

    embed = discord.Embed(
        title="✅ Bot Access Granted",
        description=(
            f"{member.mention} can now use all bot commands.\n\n"
            f"They have the same access as an admin for bot commands."
        ),
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="Granted By", value=ctx.author.mention, inline=True)
    embed.add_field(name="User ID", value=target_id, inline=True)
    embed.set_thumbnail(url=member.display_avatar.url)
    await ctx.send(embed=embed)


@bot.command()
async def ungivebotaccess(ctx, member: discord.Member):
    """Remove a member's ability to use bot commands."""
    target_id = str(member.id)

    if member.id == ctx.guild.owner_id or member.guild_permissions.administrator:
        await ctx.send(f"❌ Cannot remove bot access from {member.mention} — they are an admin or server owner.")
        return

    if target_id not in bot_allowed_users:
        await ctx.send(f"⚠️ {member.mention} doesn't have custom bot access.")
        return

    bot_allowed_users.remove(target_id)
    save_bot_access()

    embed = discord.Embed(
        title="🚫 Bot Access Removed",
        description=(
            f"{member.mention} can no longer use bot commands.\n\n"
            f"• ❌ Custom bot access has been removed\n"
            f"• They can only use commands if they are an admin or server owner"
        ),
        color=discord.Color.red(),
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="Removed By", value=ctx.author.mention, inline=True)
    embed.add_field(name="User ID", value=target_id, inline=True)
    embed.set_thumbnail(url=member.display_avatar.url)
    await ctx.send(embed=embed)


@bot.command()
async def botaccesslist(ctx):
    """Show all members with custom bot access."""
    if not bot_allowed_users:
        await ctx.send("✅ No members currently have custom bot access.")
        return

    lines = []
    for i, user_id in enumerate(bot_allowed_users, start=1):
        member = ctx.guild.get_member(int(user_id))
        name = member.mention if member else f"`<{user_id}>` (not in server)"
        lines.append(f"**{i}.** {name}")

    embed = discord.Embed(
        title="🎟️ Members With Bot Access",
        description="\n".join(lines),
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow()
    )
    embed.set_footer(text=f"Total: {len(bot_allowed_users)} member(s)")
    await ctx.send(embed=embed)


@givebotaccess.error
async def givebotaccess_error(ctx, error):
    if isinstance(error, MissingRequiredArgument):
        await ctx.send("❌ Usage: `!givebotaccess @user`")
    else:
        print(f"Ignored exception in command givebotaccess: {error}")


@ungivebotaccess.error
async def ungivebotaccess_error(ctx, error):
    if isinstance(error, MissingRequiredArgument):
        await ctx.send("❌ Usage: `!ungivebotaccess @user`")
    else:
        print(f"Ignored exception in command ungivebotaccess: {error}")


@bot.command()
async def readhistoryall(ctx):
    guild = ctx.guild
    status = await ctx.send("⏳ Enabling read-history for all non-admin roles in every text channel…")
    updated_channels = 0
    updated_roles = 0
    skipped = 0
    for channel in guild.text_channels:
        bot_perms = channel.permissions_for(guild.me)
        if not bot_perms.manage_channels:
            skipped += 1
            continue
        for role in guild.roles:
            if role.is_default():
                continue
            if role.permissions.administrator:
                continue
            if role >= guild.me.top_role:
                continue
            overwrite = channel.overwrites_for(role)
            if overwrite.read_message_history is True:
                continue
            try:
                await channel.set_permissions(role, view_channel=None, read_message_history=True)
                updated_roles += 1
            except discord.Forbidden:
                continue
            except discord.HTTPException:
                await asyncio.sleep(2)
                try:
                    await channel.set_permissions(role, view_channel=None, read_message_history=True)
                    updated_roles += 1
                except discord.HTTPException:
                    continue
            await asyncio.sleep(0.25)
        updated_channels += 1
    embed = discord.Embed(
        title="📜 Read History Enabled (All Channels)",
        description=f"Updated **{updated_channels}** channel(s) and applied **{updated_roles}** overwrite(s).\nSkipped **{skipped}** channel(s) where I don't have permission.",
        color=discord.Color.blue(), timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
    embed.set_footer(text="Admins can already read history.")
    await status.edit(content=None, embed=embed)


@bot.command()
async def readhistoryhere(ctx):
    guild = ctx.guild
    channel = ctx.channel
    bot_perms = channel.permissions_for(guild.me)
    if not bot_perms.manage_channels:
        await ctx.send("❌ I don't have permission to edit this channel's permissions.")
        return
    updated_roles = 0
    for role in guild.roles:
        if role.is_default():
            continue
        if role.permissions.administrator:
            continue
        if role >= guild.me.top_role:
            continue
        overwrite = channel.overwrites_for(role)
        if overwrite.read_message_history is True:
            continue
        try:
            await channel.set_permissions(role, view_channel=None, read_message_history=True)
            updated_roles += 1
        except discord.Forbidden:
            continue
        except discord.HTTPException:
            await asyncio.sleep(2)
            try:
                await channel.set_permissions(role, view_channel=None, read_message_history=True)
                updated_roles += 1
            except discord.HTTPException:
                continue
        await asyncio.sleep(0.25)
    embed = discord.Embed(
        title="📜 Read History Enabled (This Channel)",
        description=f"Applied `read_message_history=True` for **{updated_roles}** non-admin role(s) in {channel.mention}.",
        color=discord.Color.blue(), timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
    embed.set_footer(text="Admins can already read history.")
    await ctx.send(embed=embed)


@bot.group(invoke_without_command=True)
async def role(ctx):
    embed = discord.Embed(title="🎭 Role Manager", description="Manage roles for members.", color=discord.Color.blue())
    embed.add_field(name="Usage", value="`!role add @user @role1 @role2 ...`\n`!role remove @user @role1 @role2 ...`\n`!role list @user`", inline=False)
    await ctx.send(embed=embed)


@role.command()
async def add(ctx, member: discord.Member, *, roles: str):
    role_objs = await _resolve_roles(ctx, roles)
    if not role_objs:
        return
    added = []
    failed = []
    for r in role_objs:
        if r >= ctx.guild.me.top_role:
            failed.append(f"{r.name} (higher than my role)")
            continue
        if r in member.roles:
            failed.append(f"{r.name} (already has it)")
            continue
        try:
            await member.add_roles(r, reason=f"Added by {ctx.author}")
            added.append(r.name)
        except discord.Forbidden:
            failed.append(f"{r.name} (no permission)")
        except discord.HTTPException:
            failed.append(f"{r.name} (error)")
    await _send_role_result(ctx, member, added, failed, action="Added")


@role.command()
async def remove(ctx, member: discord.Member, *, roles: str):
    role_objs = await _resolve_roles(ctx, roles)
    if not role_objs:
        return
    removed = []
    failed = []
    for r in role_objs:
        if r not in member.roles:
            failed.append(f"{r.name} (doesn't have it)")
            continue
        try:
            await member.remove_roles(r, reason=f"Removed by {ctx.author}")
            removed.append(r.name)
        except discord.Forbidden:
            failed.append(f"{r.name} (no permission)")
        except discord.HTTPException:
            failed.append(f"{r.name} (error)")
    await _send_role_result(ctx, member, removed, failed, action="Removed")


@role.command()
async def list(ctx, member: discord.Member):
    if not member.roles[1:]:
        await ctx.send(f"✅ {member.mention} has no custom roles.")
        return
    role_list = "\n".join([r.mention for r in member.roles[1:]])
    embed = discord.Embed(
        title=f"🎭 Roles for {member.display_name}",
        description=role_list,
        color=member.color if member.color != discord.Color.default() else discord.Color.blue()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    await ctx.send(embed=embed)


async def _resolve_roles(ctx, roles_str: str):
    tokens = roles_str.split()
    role_objs = []
    not_found = []
    for token in tokens:
        role = None
        if token.startswith("<@&") and token.endswith(">"):
            try:
                rid = int(token[3:-1])
                role = ctx.guild.get_role(rid)
            except ValueError:
                pass
        elif token.isdigit():
            role = ctx.guild.get_role(int(token))
        else:
            role = discord.utils.get(ctx.guild.roles, name=token)
        if role is None:
            not_found.append(token)
        else:
            role_objs.append(role)
    if not_found:
        await ctx.send(f"❌ Could not find role(s): {', '.join(not_found)}")
    return role_objs


async def _send_role_result(ctx, member, success_list, fail_list, action):
    color = discord.Color.green() if success_list and not fail_list else (
        discord.Color.orange() if success_list and fail_list else discord.Color.red()
    )
    embed = discord.Embed(title=f"🎭 {action} Roles for {member.display_name}", color=color, timestamp=discord.utils.utcnow())
    if success_list:
        embed.add_field(name=f"✅ {action}", value="\n".join(success_list), inline=False)
    if fail_list:
        embed.add_field(name="❌ Skipped", value="\n".join(fail_list), inline=False)
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
    await ctx.send(embed=embed)


@discord.ext.commands.cooldown(1, 300, discord.ext.commands.BucketType.channel)
@bot.command()
async def pingeveryone(ctx, *, message: str = "📢 Attention everyone!"):
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass
    embed = discord.Embed(title="📢 Announcement", description=message, color=discord.Color.gold(), timestamp=discord.utils.utcnow())
    embed.set_author(name=f"Sent by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
    await ctx.send(content="@everyone", embed=embed)


@pingeveryone.error
async def pingeveryone_error(ctx, error):
    if isinstance(error, discord.ext.commands.CommandOnCooldown):
        seconds = int(error.retry_after)
        minutes, secs = divmod(seconds, 60)
        await ctx.send(f"⏳ This command is on cooldown. Try again in **{minutes}m {secs}s**.", delete_after=5)
    else:
        print(f"Ignored exception in command pingeveryone: {error}")


@bot.command()
async def say(ctx, *, content: str):
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass
    if content.lower().startswith("embed "):
        rest = content[6:].strip()
        if "|" in rest:
            title, message = rest.split("|", 1)
            title = title.strip() or "Announcement"
            message = message.strip()
        else:
            title = "Announcement"
            message = rest
        embed = discord.Embed(title=title, description=message, color=discord.Color.blue(), timestamp=discord.utils.utcnow())
        embed.set_author(name=f"Sent by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)
        return
    await ctx.send(content)


@bot.command()
async def private(ctx):
    guild = ctx.guild
    channel = ctx.channel
    member_role = guild.get_role(TARGET_ROLE_ID)
    if member_role is None:
        await ctx.send(f"❌ Role with ID `{TARGET_ROLE_ID}` not found.")
        return
    try:
        await channel.set_permissions(
            guild.default_role,
            view_channel=False, send_messages=False, read_message_history=False,
            connect=False, speak=False,
        )
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to edit this channel.")
        return
    try:
        await channel.set_permissions(
            member_role,
            view_channel=True, send_messages=True, read_message_history=True,
            connect=True, speak=True,
        )
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to edit this channel.")
        return
    embed = discord.Embed(
        title="🙈 Channel Set to Private",
        description=f"{channel.mention} is now **private**.\n\n• **@{guild.default_role.name}** can no longer see or send messages.\n• **{member_role.name}** and **Admins** can access it.",
        color=discord.Color.dark_purple(), timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
    await ctx.send(embed=embed)


@bot.command()
async def public(ctx):
    guild = ctx.guild
    channel = ctx.channel
    member_role = guild.get_role(TARGET_ROLE_ID)
    try:
        await channel.set_permissions(guild.default_role, overwrite=None)
        if member_role is not None:
            await channel.set_permissions(member_role, overwrite=None)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to edit this channel.")
        return
    embed = discord.Embed(
        title="🔓 Channel Set to Public",
        description=f"{channel.mention} is now public for everyone.",
        color=discord.Color.green(), timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
    await ctx.send(embed=embed)


@bot.command()
async def secure(ctx):
    guild = ctx.guild
    channel = ctx.channel
    role = guild.default_role
    try:
        await channel.set_permissions(role, overwrite=None)
        overwrite = discord.PermissionOverwrite(
            mention_everyone=False, attach_files=False, embed_links=False,
        )
        await channel.set_permissions(role, overwrite=overwrite)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to edit this channel's permissions. Make sure my role is above the @everyone role.")
        return
    embed = discord.Embed(
        title="🛡️ Channel Secured",
        description=f"Security restrictions applied to {ctx.channel.mention}:\n• ❌ **@everyone / @here mentions** are now blocked\n• ❌ **File uploads** are now blocked\n• ❌ **Embeds** are now blocked",
        color=discord.Color.dark_grey(), timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
    await ctx.send(embed=embed)


@bot.command()
async def unsecure(ctx):
    guild = ctx.guild
    channel = ctx.channel
    role = guild.default_role
    try:
        overwrite = discord.PermissionOverwrite(
            mention_everyone=None, attach_files=None, embed_links=None,
        )
        await channel.set_permissions(role, overwrite=overwrite)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to edit this channel's permissions. Make sure my role is above the @everyone role.")
        return
    embed = discord.Embed(
        title="🔓 Channel Unsecured",
        description=f"{ctx.channel.mention} security restrictions have been lifted:\n• ✅ @everyone / @here mentions allowed\n• ✅ File uploads allowed\n• ✅ Embeds allowed",
        color=discord.Color.green(), timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
    await ctx.send(embed=embed)


@bot.command()
async def slowmode(ctx, seconds: str):
    if seconds.lower() == "off":
        await ctx.channel.edit(slowmode_delay=0)
        embed = discord.Embed(title="🐌 Slowmode Disabled", description=f"Slowmode in {ctx.channel.mention} is now off.", color=discord.Color.green())
        await ctx.send(embed=embed)
        return
    try:
        sec = int(seconds)
        if sec < 0 or sec > 21600:
            raise ValueError
    except ValueError:
        await ctx.send("❌ Provide a number of seconds between 0 and 21600, or 'off'.")
        return
    await ctx.channel.edit(slowmode_delay=sec)
    embed = discord.Embed(title="🐌 Slowmode Updated", description=f"Slowmode in {ctx.channel.mention} set to **{sec} second(s)**.", color=discord.Color.orange())
    await ctx.send(embed=embed)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, CheckFailure):
        await ctx.send("❌ Only the server owner or admins can use this bot.")
    elif isinstance(error, MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    elif isinstance(error, MissingRequiredArgument):
        await ctx.send("❌ Missing required argument.")
    elif isinstance(error, BadArgument):
        await ctx.send("❌ One or more arguments are invalid.")
    else:
        print(f"Ignored exception in command {ctx.command}: {error}")


# ============== TOKEN (FROM RAILWAY VARIABLE) ==============
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN is None:
    print("❌ ERROR: DISCORD_TOKEN not set! Add it in Railway Variables.")
    exit(1)

bot.run(TOKEN)
