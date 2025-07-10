import discord
from discord.ext import commands, tasks
import json
import os
import random
from datetime import timedelta, datetime
import aiohttp
from aiohttp import web
from pymongo import MongoClient, DESCENDING
import threading
from flask import Flask

mongo_uri = "mongodb://localhost:27017/myDatabase"

# Replace with your actual URI
mongo_uri = "mongodb://localhost:27017/myDatabase"
client = MongoClient(mongo_uri)

try:
    db = client.myDatabase  # Access your database
    print("Connected to MongoDB!")
    # Your operations here
finally:
    client.close()

# Flask app definition
app = Flask(__name__)

@app.route('/')
def home():
    return "Hello, Replit!"

TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    print("ERROR: DISCORD_TOKEN is not set")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
WELCOME_CHANNEL_ID = 1332817863135723531
LOG_CHANNEL_ID = 1392463222103212144
COMMANDS_CHANNEL_ID = 1290295233300402227
MODERATOR_ROLE_NAME = '🛡 Модератор'
REQUIRED_ROLE_NAME = '✭'
TwitchChannel = 'ShenFRusH'
TWITCH_CLIENT_ID = os.getenv('TWITCH_CLIENT_ID')
TWITCH_CLIENT_SECRET = os.getenv('TWITCH_CLIENT_SECRET')
TWITCH_OAUTH_TOKEN = os.getenv('TWITCH_OAUTH_TOKEN')
NOTIFY_CHANNEL_ID = 1332817863135723531 
TwitchAPIURL = 'https://api.twitch.tv/helix/streams?user_login=ShenFRusH'
is_streaming = False
mongo_uri = os.getenv('MONGO_URI')
mongo_client = MongoClient(mongo_uri, tls=True, tlsAllowInvalidCertificates=True)
db = mongo_client["shenbot"]
users_collection = db["users"]


def get_user_data(user_id):
    user = users_collection.find_one({"_id": str(user_id)})
    if not user:
        user = {"_id": str(user_id), "xp": 0, "level": 0, "last_message_day": str(datetime.today().date())}
        users_collection.insert_one(user)
    return user

def update_user_data(user_id, data):
    result = users_collection.update_one({"_id": str(user_id)}, {"$set": data}, upsert=True)
    print(f"Обновлено документов: {result.modified_count}, апсертов: {result.upserted_id}")

async def check_stream_status():
    global is_streaming
    headers = {
        'Client-ID': TWITCH_CLIENT_ID,
        'Authorization': f'Bearer {TWITCH_OAUTH_TOKEN}'
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(TwitchAPIURL, headers=headers) as response:
            data = await response.json()
            print(data)  # Логируем весь ответ для отладки
            if 'data' in data:  # Проверяем, что ключ 'data' существует в ответе
                if data['data']: 
                    stream_info = data['data'][0]
                    viewer_count = stream_info['viewer_count'] 
                    if not is_streaming: 
                        is_streaming = True
                        await send_stream_notification(viewer_count)
                else:
                    is_streaming = False
            else:
                print("Нет данных в ответе Twitch API!")
                is_streaming = False
async def send_stream_notification(viewer_count):
    channel = bot.get_channel(NOTIFY_CHANNEL_ID)  
    stream_url = f"https://www.twitch.tv/{TwitchChannel}"  
    stream_title = "Шен подрубил стрим!"  
    game_name = "Minecraft"  
    embed = discord.Embed(
        title=f"🎮 **{stream_title}**",
        description=f"**Игра:** {game_name}\n**Заголовок стрима:** {stream_title}\n**Зрителей:** {viewer_count}",
        color=discord.Color.purple()
    )
    embed.add_field(name="💥 Присоединяйтесь к стриму!", value=f"**[Перейти на стрим]({stream_url})**", inline=False)
    embed.set_footer(text="Shenята | TWITCH")
    if channel:
        await channel.send(f"@everyone Шен подрубил стрим! Заходите, не пропустите!", embed=embed)
@tasks.loop(minutes=1)  
async def auto_notify_stream():
    await check_stream_status()
@bot.event
async def on_ready():
    print(f'Бот {bot.user} подключён к Discord!')
    auto_notify_stream.start() 
LEVEL_ROLES = {
    10: '🟥 Паралелепипед',
    15: '👾 Полупок',
    20: '✨ VIP',
}
GIF_WELCOME_URL = 'https://media.discordapp.net/attachments/685815150376255502/1282276742664425504/TIIINzVMap8.gif'
GIF_GOODBYE_URL = 'https://media.discordapp.net/attachments/937113595219693588/1333162715853623406/ezgif-2-bb540f2ee7.gif'
def has_required_role():
    async def predicate(ctx):
        role = discord.utils.get(ctx.author.roles, name=REQUIRED_ROLE_NAME)
        if role is None:
            await ctx.send("🚫 У тебя нет прав на выполнение этой команды!")
            return False
        return True
    return commands.check(predicate)
@bot.event
async def on_ready():
    print(f'Бот {bot.user} подключён к Discord!')

    for guild in bot.guilds:
        for member in guild.members:
            if member.bot:
                continue
            user_id = str(member.id)
            get_user_data(user_id)  # просто инициализируем, если не существует

    auto_notify_stream.start()
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.content.startswith(bot.command_prefix):
        await bot.process_commands(message)
        return
    user_id = str(message.author.id)
    user_data = get_user_data(user_id)  # получаем или создаём в базе

    current_day = str(datetime.today().date())
    if user_data['last_message_day'] != current_day:
        xp_gain = random.randint(10, 15)
        user_data['last_message_day'] = current_day
    else:
        xp_gain = random.randint(1, 5)
    user_data["xp"] += xp_gain  # <- тут был пропуск, нужно прибавлять XP всегда
    update_user_data(user_id, user_data)  # сохраняем в MongoDB

    current_xp = user_data["xp"]
    current_level = user_data["level"]
    new_level = 0
    while current_xp >= (new_level + 1) * 100 + 500:
        new_level += 1
    if new_level > current_level:
        old_level = current_level
        user_data["level"] = new_level
        update_user_data(user_id, user_data)

        guild = message.guild
        member = message.author
        for lvl, role_name in LEVEL_ROLES.items():
            role = discord.utils.get(guild.roles, name=role_name)
            if role and role in member.roles and lvl > new_level:
                await member.remove_roles(role)
        give_role_name = None
        for lvl, role_name in sorted(LEVEL_ROLES.items()):
            if new_level >= lvl:
                give_role_name = role_name
            else:
                break
        if give_role_name:
            role = discord.utils.get(guild.roles, name=give_role_name)
            if role and role not in member.roles:
                await member.add_roles(role)
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="🔼 Повышение уровня",
                description=(f"Пользователь: {member.mention}\nСтарый уровень: {old_level}\nНовый уровень: {new_level}\nТекущий XP: {user_data['xp']}"),
                color=discord.Color.green()
            )
            embed.set_footer(text="Shenята | TWITCH")
            await log_channel.send(embed=embed)
    await bot.process_commands(message)
@bot.command(name='модер')
@has_required_role()
@commands.has_permissions(manage_roles=True, manage_messages=True)
async def moder(ctx):
    if not ctx.message.mentions:
        await ctx.send('Пожалуйста, укажи пользователя через @упоминание.')
        return
    member = ctx.message.mentions[0]
    role = discord.utils.get(ctx.guild.roles, name=MODERATOR_ROLE_NAME)
    if role is None:
        await ctx.send(f'Роль "{MODERATOR_ROLE_NAME}" не найдена.')
        return
    try:
        await member.add_roles(role, reason=f'Выдана роль модера по команде {ctx.author}') 
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="✅ Роль модератора выдана",
                description=f"Модератор: {ctx.author.mention}\nПользователь: {member.mention}\nДата: {ctx.message.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
                color=discord.Color.green()
            )
            embed.set_footer(text="Shenята | TWITCH")
            await log_channel.send(embed=embed)

        channel = bot.get_channel(WELCOME_CHANNEL_ID)
        if channel is None:
            await ctx.send('Канал для приветствия не найден.')
            return
        embed = discord.Embed(
            title="🚀 Новый модератор на борту!",
            description=(
                f"🎮 Загрузка модератора: {member.mention}...\n"
                "✅ Рады видеть тебя в Shenята | TWITCH!\n"
                "🛡️ Вперёд, к новым победам и справедливости!"
            ),
            color=discord.Color.blue()
        )
        embed.set_image(url=GIF_WELCOME_URL)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Shenята | TWITCH")
        await channel.send(embed=embed)
    except discord.Forbidden:
        await ctx.send('❌ У меня нет прав на изменение ролей или удаление сообщений.')
    except Exception as e:
        await ctx.send(f"⚠️ Ошибка: {e}")
@bot.command(name='снять')
@has_required_role()
@commands.has_permissions(manage_roles=True)
async def remove_mod(ctx):
    if not ctx.message.mentions:
        await ctx.send('Пожалуйста, укажи пользователя через @упоминание.')
        return
    member = ctx.message.mentions[0]
    role = discord.utils.get(ctx.guild.roles, name=MODERATOR_ROLE_NAME)
    if role is None:
        await ctx.send(f'Роль "{MODERATOR_ROLE_NAME}" не найдена.')
        return
    try:
        # Снимаем роль модератора
        await member.remove_roles(role, reason=f'Снятие роли модера по команде {ctx.author}')

        # Логирование действия
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="❌ Роль модератора снята",
                description=f"Модератор: {ctx.author.mention}\nПользователь: {member.mention}\nДата: {ctx.message.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
                color=discord.Color.red()
            )
            embed.set_footer(text="Shenята | TWITCH")
            await log_channel.send(embed=embed)

        # Прощальное сообщение
        channel = bot.get_channel(WELCOME_CHANNEL_ID)
        if channel is None:
            await ctx.send('Канал для прощания не найден.')
            return
        embed = discord.Embed(
            title="👋 Модератор покидает пост",
            description=(
                f"🎮 Снятие роли модератора: {member.mention}...\n"
                "✅ Спасибо за твою работу в Shenята | TWITCH!\n"
                "🛡️ Удачи и новых достижений!"
            ),
            color=discord.Color.red()
        )
        embed.set_image(url=GIF_GOODBYE_URL)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Shenята | TWITCH")
        await channel.send(embed=embed)

    except discord.Forbidden:
        await ctx.send('❌ У меня нет прав на изменение ролей.')
    except Exception as e:
        await ctx.send(f"⚠️ Ошибка: {e}")
@bot.command(name='ранг')
async def rank(ctx, member: discord.Member = None):
    # Проверка, чтобы команда использовалась только в нужном канале или пользователем с ролью ✭
    if not discord.utils.get(ctx.author.roles, name='✭') and ctx.channel.id != COMMANDS_CHANNEL_ID:
        await ctx.message.delete()  # Удаляем сообщение пользователя
        msg = await ctx.send(f"⚠️ Используй эту команду только в канале <#{COMMANDS_CHANNEL_ID}>.")  # Уведомление
        await msg.delete(delay=3)  # Удаляем уведомление через 3 секунды
        return  # Завершаем выполнение команды, если не в нужном канале или без роли ✭

    # Если не указан участник, показываем карточку ранга для самого себя
    if not member:
        member = ctx.author

    # Проверка прав для просмотра ранга другого пользователя
    can_view_other_rank = any(role.name == REQUIRED_ROLE_NAME for role in ctx.author.roles) or any(role.name == MODERATOR_ROLE_NAME for role in ctx.author.roles)
    if member != ctx.author and not can_view_other_rank:
        await ctx.send("🚫 У тебя нет прав для просмотра чужого ранга!")
        return

    # Получаем данные пользователя
    user_id = str(member.id)
    user_data = get_user_data(user_id)
    level = user_data["level"]
    xp = user_data["xp"]

    # Расчёт XP для следующего уровня
    next_level_xp = (level * 100) + 200  # Меняем формулу для следующего уровня
    xp_needed = max(0, next_level_xp - xp)  # Покажем сколько XP нужно для следующего уровня

    # Создание embed карточки
    embed = discord.Embed(title=f"Карточка игрока: {member.display_name}", color=discord.Color.blue())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Уровень", value=str(level))
    embed.add_field(name="XP", value=f"{xp} / {next_level_xp}")
    embed.add_field(name="До следующего уровня", value=f"{xp_needed} XP")

    await ctx.send(embed=embed)
@bot.command(name='топ')
async def top(ctx):
    if not discord.utils.get(ctx.author.roles, name='✭') and ctx.channel.id != COMMANDS_CHANNEL_ID:
        await ctx.message.delete()
        msg = await ctx.send(f"⚠️ Используй эту команду только в канале <#{COMMANDS_CHANNEL_ID}>.")
        await msg.delete(delay=3)
        return

    top_users = list(users_collection.find().sort([("level", DESCENDING), ("xp", DESCENDING)]).limit(10))
    if not top_users:
        await ctx.send("Пока никто не набрал XP.")
        return

    embed = discord.Embed(title="🔥 Топ 10 по уровню", color=discord.Color.blue())
    for i, user_data in enumerate(top_users):
        member = ctx.guild.get_member(int(user_data["_id"]))
        name = member.display_name if member else f"Пользователь {user_data['_id']}"
        level = user_data["level"]
        xp = user_data["xp"]
        next_level_xp = (level * 100) + 200
        embed.add_field(
            name=f"{i + 1}. {name}",
            value=f"Уровень: **{level}**\nXP: **{xp}** / {next_level_xp}",
            inline=False
        )

    await ctx.send(embed=embed)
@bot.command(name='установить')
@has_required_role()
async def set_level(ctx, member: discord.Member, level: int):
    user_id = str(member.id)
    user_data = get_user_data(user_id)
    old_level = user_data.get("level", 0)
    user_data["level"] = level
    user_data["xp"] = (level ** 2) * 10
    update_user_data(user_id, user_data)
    for lvl, role_name in LEVEL_ROLES.items():
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if role and role in member.roles:
            await member.remove_roles(role)
    give_role_name = None
    for lvl, role_name in sorted(LEVEL_ROLES.items()):
        if level >= lvl:
            give_role_name = role_name
        else:
            break
    if give_role_name:
        role = discord.utils.get(ctx.guild.roles, name=give_role_name)
        if role and role not in member.roles:
            await member.add_roles(role)
    await ctx.send(f"Уровень пользователя {member.mention} изменён с {old_level} на {level}.")
    log_channel = bot.get_channel(LOG_CHANNEL_ID)    
    if log_channel:
        embed = discord.Embed(
            title="⚙️ Уровень установлен вручную",
            description=(
                f"Модератор: {ctx.author.mention}\n"
                f"Пользователь: {member.mention}\n"
                f"Старый уровень: {old_level}\n"
                f"Новый уровень: {level}\n"
                f"Дата: {ctx.message.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
            ),
            color=discord.Color.orange()
        )
        embed.set_footer(text="Shenята | TWITCH")
        await log_channel.send(embed=embed)
fairy_tales = [
    {
        "title": "Сказка о храброй принцессе и драконах",
        "story": (
            "В далеком королевстве, где солнце никогда не заходило, жила принцесса по имени Элис. "
            "Она была не как все принцессы — вместо того чтобы сидеть в замке, она любила гулять по лесам и "
            "помогать тем, кто нуждался в защите. Однажды, на закате, когда туман еще не рассеялся, "
            "к королевству подлетели два дракона, огромных и страшных. Они разрушали все на своем пути.\n\n"
            "Принцесса Элис, несмотря на страх, не побежала в укрытие. Вместо этого она села на своего верного коня, "
            "отрядив его в направлении замка, и взяла меч — древний артефакт, передавшийся ей по наследству. "
            "Она отправилась в глубь леса, чтобы найти источник силы этих чудовищ.\n\n"
            "После долгих поисков принцесса наткнулась на волшебное озеро, где встретила старую колдунью. "
            "Колдунья рассказала, что драконы были магическими созданиями, которым необходима сила древней магии для их контроля. "
            "Но чтобы победить драконов, принцессе нужно было взять силу в свои руки и воссоединиться с древней магией.\n\n"
            "С каждым шагом к драконам, Элис становилась сильнее. И, наконец, на поле битвы, она сразилась с первым драконом. "
            "С помощью силы артефакта и своей воли ей удалось победить чудовища. Второй дракон, увидев свою погибшую сестру, побежал прочь. "
            "Элис вернулась в королевство как героиня, а королевство навсегда осталось в мире, благодаря храбрости принцессы."
        )
    },
    {
        "title": "Тайна Лесного Острова",
        "story": (
            "Среди зеленых просторов Лесного Королевства скрывался таинственный остров, который никто не осмеливался посещать. "
            "Легенды о нем ходили в округе, но никто не знал точно, что там скрыто.\n\n"
            "Однажды, молодой путешественник по имени Лука, решив разгадать эту загадку, отправился на этот загадочный остров. "
            "Поднявшись на корабле через бушующие волны, он наконец достиг земли, скрытой под темными деревьями.\n\n"
            "Лука шел по старым тропинкам, и вскоре заметил, что вокруг него все меняется. Деревья становились все выше, а воздух — все холоднее. "
            "Наконец, он достиг странного камня, на котором было написано таинственное послание. Только тот, кто не побоится столкнуться с тенью, "
            "сможет раскрыть истинную силу острова.\n\n"
            "Лука не колебался и решил продолжить путешествие. На самом острове он встретил древнего стража, который рассказал, что остров является "
            "местом силы, а камни, которые Лука увидел, — это ключи к древним знаниям, спрятанным там.\n\n"
            "С помощью магических камней и решимости, Лука сумел открыть тайные врата, ведущие к загадочному магическому источнику, "
            "который даровал ему невероятные силы и понимание самого мира. Остров Лесного Королевства остался нетронутым, а его тайны были раскрыты."
        )
    },
    {
        "title": "Приключения Синих Звезд",
        "story": (
            "Много лет назад в небесах жил молодой маг, известный как Астрас. Он обладал волшебной силой, которая позволяла "
            "ему управлять звездным светом и использовать его в самых разнообразных целях. Его называли магом ночного света.\n\n"
            "Однажды ночью, когда звездное небо было особенно ясным, Астрас заметил одну странную звезду, которая не двигалась, "
            "как другие, а наоборот, начинала опускаться к земле. Он решился отправиться за ней.\n\n"
            "Когда он приземлился в лесу, звезда оказалась не просто куском небесного света, а живым существом. Это была "
            "волшебная птица, зовущаяся Синей Звездой. Птица объяснила, что она потеряла связь с небесами и теперь нуждается в помощи, "
            "чтобы вернуться домой.\n\n"
            "Астрас и Синяя Звезда отправились в путешествие по магическим землям, где их ждала немалая опасность. "
            "Вскоре они обнаружили, что силы тьмы пытаются захватить этот мир, и именно Синяя Звезда может стать последним "
            "ключом к сохранению мира.\n\n"
            "С храбростью, решимостью и волшебными силами Астрас и Синяя Звезда одолели темные силы и вернули мир в гармонию. "
            "Звезда вернулась на небо, а маг, познавший истинное значение света, вернулся домой с миром в своем сердце."
        )
    }
]
@bot.command(name='сказка')
async def fairy_tale(ctx):
    if not discord.utils.get(ctx.author.roles, name='✭') and ctx.channel.id != COMMANDS_CHANNEL_ID:
        await ctx.message.delete()
        msg = await ctx.send(f"⚠️ Используй эту команду только в канале <#{COMMANDS_CHANNEL_ID}>.")
        await msg.delete(delay=3)
        return
    tale = random.choice(fairy_tales) 
    title = tale["title"]
    story = tale["story"]
    embed = discord.Embed(
        title=title,
        description=story,
        color=discord.Color.purple()
    )
    embed.set_footer(text="Shenята | TWITCH - Сказка на ночь")
    await ctx.send(embed=embed) 
@bot.command(name='помощь')
async def help_command(ctx):
    # Проверяем, есть ли у пользователя роль "✭" или он в нужном канале
    if not discord.utils.get(ctx.author.roles, name='✭') and ctx.channel.id != COMMANDS_CHANNEL_ID:
        await ctx.message.delete()  # Удаляем сообщение
        msg = await ctx.send(f"⚠️ Используй эту команду только в канале <#{COMMANDS_CHANNEL_ID}>.")
        await msg.delete(delay=3)  # Удаляем сообщение после 3 секунд
        return

    help_text = "**Доступные команды:**\n"

    # Если у пользователя есть роль "✭", то добавляем дополнительные команды
    if discord.utils.get(ctx.author.roles, name='✭'):
        help_text += (
            "**🎮 Развлечения:**\n"
            "`!сказка` — Розкажет вам казку на ночь.\n"
            "\n"
            "**🔸 Команды куратора (для ✭):**\n"
            "`!модер @пользователь` — выдать роль Модератор и приветствовать.\n"
            "`!снять @пользователь` — снять роль Модератор.\n"
            "`!установить <пользователь> <уровень>` — установить уровень.\n"
            "\n"
            "**💥 Команды модератора:**\n"
            "`!мьют @пользователь <время>` — замутить пользователя на заданное время.\n"
            "`!размьют @пользователь` — размутить пользователя.\n"
            "`!бан @пользователь <причина>` — забанить пользователя.\n"
            "`!разбан @пользователь` — разбанить пользователя.\n"
            "`!кик @пользователь <причина>` — кикнуть пользователя.\n"
            "\n"
            "**🔹 Рейтинг:**\n"
            "`!ранг` — показать свой уровень и XP или ранг другого пользователя (для модераторов и ✭).\n"
            "`!топ` — показать топ 10 по уровню.\n"
        )
    # Для модератора
    elif discord.utils.get(ctx.author.roles, name=MODERATOR_ROLE_NAME):
        help_text += (
            "**💥 Команды модератора:**\n"
            "`!мьют @пользователь <время>` — замутить пользователя на заданное время.\n"
            "`!размьют @пользователь` — размутить пользователя.\n"
            "`!бан @пользователь <причина>` — забанить пользователя.\n"
            "`!разбан @пользователь` — разбанить пользователя.\n"
            "`!кик @пользователь <причина>` — кикнуть пользователя.\n"
            "\n"
            "**🔹 Рейтинг:**\n"
            "`!ранг` — показать свой уровень и XP.\n"
            "`!топ` — показать топ 10 по уровню.\n"
        )
    # Для обычных пользователей
    else:
        help_text += (
            "**🔹 Рейтинг:**\n"
            "`!ранг` — показать свой уровень и XP.\n"
            "`!топ` — показать топ 10 по уровню.\n"
        )

    from aiohttp import web
    import threading

    async def handle(request):
        return web.Response(text="Bot is running")

    app = web.Application()
    app.router.add_get('/', handle)

    def run_web():
        web.run_app(app, port=3000)

    threading.Thread(target=run_web).start()

    await ctx.send(help_text)

def has_moderator_role():
    async def predicate(ctx):
        has_star = discord.utils.get(ctx.author.roles, name=REQUIRED_ROLE_NAME)
        has_mod = discord.utils.get(ctx.author.roles, name=MODERATOR_ROLE_NAME)
        if has_star is None and has_mod is None:
            await ctx.send("🚫 У тебя нет прав на выполнение этой команды!")
            return False
        return True
    return commands.check(predicate)

@bot.command(name='мьют')
@has_moderator_role()
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member = None, *, args="10m"):
    if member is None:
        await ctx.send("Укажи пользователя для мьюта!")
        return
    
    if member == ctx.author:
        await ctx.send("Ты не можешь замутить самого себя!")
        return
    
    # Проверяем, есть ли роль "Muted"
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        # Создаем роль "Muted" если её нет
        muted_role = await ctx.guild.create_role(name="Muted", reason="Роль для мьюта")
        # Запрещаем отправлять сообщения во всех каналах
        for channel in ctx.guild.channels:
            await channel.set_permissions(muted_role, send_messages=False, add_reactions=False)
    
    # Парсим аргументы: время и причину
    parts = args.split(' ', 1)  # Разделяем на максимум 2 части
    duration = parts[0]
    reason = parts[1] if len(parts) > 1 else "Причина не указана"
    
    # Парсим время (поддержка русского и английского)
    time_dict = {
        "s": 1, "с": 1, "sec": 1, "сек": 1,
        "m": 60, "м": 60, "min": 60, "мин": 60,
        "h": 3600, "ч": 3600, "hour": 3600, "час": 3600,
        "d": 86400, "д": 86400, "day": 86400, "день": 86400
    }
    
    # Ищем число и единицу времени
    import re
    match = re.match(r'(\d+)([a-zA-Zа-яА-Я]+)', duration)
    if not match:
        await ctx.send("Неверный формат времени! Используй: 10м, 5h, 2д, 30min и т.д.")
        return
    
    time_amount = int(match.group(1))
    time_unit = match.group(2).lower()
    
    if time_unit not in time_dict:
        await ctx.send("Неверная единица времени! Используй: с/s, м/m, ч/h, д/d")
        return
    
    mute_seconds = time_amount * time_dict[time_unit]
    
    try:
        await member.add_roles(muted_role, reason=f"Мьют от {ctx.author}")
        
        # Логирование
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="🔇 Пользователь замучен",
                description=f"Модератор: {ctx.author.mention}\nПользователь: {member.mention}\nВремя: {duration}\nПричина: {reason}\nДата: {ctx.message.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
                color=discord.Color.orange()
            )
            embed.set_footer(text="Shenята | TWITCH")
            await log_channel.send(embed=embed)
        
        await ctx.send(f"🔇 {member.mention} замучен на {duration}. Причина: {reason}")
        
        # Автоматическое размьютивание
        await discord.utils.sleep_until(discord.utils.utcnow() + timedelta(seconds=mute_seconds))
        if muted_role in member.roles:
            await member.remove_roles(muted_role, reason="Автоматическое размьютивание")
            # Логирование автоматического размьюта
            if log_channel:
                embed = discord.Embed(
                    title="🔊 Автоматическое размьютивание",
                    description=f"Пользователь: {member.mention}\nВремя мьюта истекло\nДата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    color=discord.Color.green()
                )
                embed.set_footer(text="Shenята | TWITCH")
                await log_channel.send(embed=embed)
            
    except discord.Forbidden:
        await ctx.send("❌ У меня нет прав на изменение ролей!")

@bot.command(name='размьют')
@has_moderator_role()
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member = None):
    if member is None:
        await ctx.send("Укажи пользователя для размьюта!")
        return
    
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        await ctx.send("Роль 'Muted' не найдена!")
        return
    
    if muted_role not in member.roles:
        await ctx.send(f"{member.mention} не замучен!")
        return
    
    try:
        await member.remove_roles(muted_role, reason=f"Размьют от {ctx.author}")
        
        # Логирование
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="🔊 Пользователь размучен",
                description=f"Модератор: {ctx.author.mention}\nПользователь: {member.mention}\nДата: {ctx.message.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
                color=discord.Color.green()
            )
            embed.set_footer(text="Shenята | TWITCH")
            await log_channel.send(embed=embed)
        
        await ctx.send(f"🔊 {member.mention} размучен")
        
    except discord.Forbidden:
        await ctx.send("❌ У меня нет прав на изменение ролей!")

@bot.command(name='бан')
@has_moderator_role()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member = None, *, args=""):
    if member is None:
        await ctx.send("Укажи пользователя для бана!")
        return
    
    if member == ctx.author:
        await ctx.send("Ты не можешь забанить самого себя!")
        return
    
    # Парсим аргументы: время и причину
    ban_seconds = None
    reason = "Причина не указана"
    
    if args:
        parts = args.split(' ', 1)  # Разделяем на максимум 2 части
        first_part = parts[0]
        
        # Проверяем, является ли первая часть временем
        time_dict = {
            "s": 1, "с": 1, "sec": 1, "сек": 1,
            "m": 60, "м": 60, "min": 60, "мин": 60,
            "h": 3600, "ч": 3600, "hour": 3600, "час": 3600,
            "d": 86400, "д": 86400, "day": 86400, "день": 86400
        }
        
        import re
        match = re.match(r'(\d+)([a-zA-Zа-яА-Я]+)', first_part)
        if match:
            time_amount = int(match.group(1))
            time_unit = match.group(2).lower()
            
            if time_unit in time_dict:
                ban_seconds = time_amount * time_dict[time_unit]
                # Если есть вторая часть, это причина
                if len(parts) > 1:
                    reason = parts[1]
            else:
                # Если первая часть не время, то всё это причина
                reason = args
        else:
            # Если первая часть не время, то всё это причина
            reason = args
    
    try:
        await member.ban(reason=f"Забанен модератором {ctx.author}: {reason}")
        
        # Логирование
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            ban_type = f"временно на {first_part}" if ban_seconds else "навсегда"
            embed = discord.Embed(
                title="🔨 Пользователь забанен",
                description=f"Модератор: {ctx.author.mention}\nПользователь: {member.mention}\nВремя: {ban_type}\nПричина: {reason}\nДата: {ctx.message.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
                color=discord.Color.red()
            )
            embed.set_footer(text="Shenята | TWITCH")
            await log_channel.send(embed=embed)
        
        if ban_seconds:
            await ctx.send(f"🔨 {member.mention} временно забанен на {first_part}. Причина: {reason}")
            # Автоматический разбан
            await discord.utils.sleep_until(discord.utils.utcnow() + timedelta(seconds=ban_seconds))
            try:
                await ctx.guild.unban(member, reason="Автоматический разбан")
                # Логирование автоматического разбана
                if log_channel:
                    embed = discord.Embed(
                        title="✅ Автоматический разбан",
                        description=f"Пользователь: {member.mention}\nВремя бана истекло\nДата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        color=discord.Color.green()
                    )
                    embed.set_footer(text="Shenята | TWITCH")
                    await log_channel.send(embed=embed)
            except:
                pass  # Пользователь мог быть разбанен вручную
        else:
            await ctx.send(f"🔨 {member.mention} забанен навсегда. Причина: {reason}")
        
    except discord.Forbidden:
        await ctx.send("❌ У меня нет прав на бан пользователей!")

@bot.command(name='разбан')
@has_moderator_role()
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, member_name):
    banned_users = [entry async for entry in ctx.guild.bans()]
    
    for ban_entry in banned_users:
        user = ban_entry.user
        if user.name == member_name or str(user) == member_name:
            try:
                await ctx.guild.unban(user, reason=f"Разбанен модератором {ctx.author}")
                
                # Логирование
                log_channel = bot.get_channel(LOG_CHANNEL_ID)
                if log_channel:
                    embed = discord.Embed(
                        title="✅ Пользователь разбанен",
                        description=f"Модератор: {ctx.author.mention}\nПользователь: {user.mention}\nДата: {ctx.message.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
                        color=discord.Color.green()
                    )
                    embed.set_footer(text="Shenята | TWITCH")
                    await log_channel.send(embed=embed)
                
                await ctx.send(f"✅ {user.mention} разбанен")
                return
                
            except discord.Forbidden:
                await ctx.send("❌ У меня нет прав на разбан пользователей!")
                return
    
    await ctx.send("Пользователь с таким именем не найден в списке забаненных!")

@bot.command(name='кик')
@has_moderator_role()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member = None, *, reason="Причина не указана"):
    if member is None:
        await ctx.send("Укажи пользователя для кика!")
        return
    
    if member == ctx.author:
        await ctx.send("Ты не можешь кикнуть самого себя!")
        return
    
    try:
        await member.kick(reason=f"Кикнут модератором {ctx.author}: {reason}")
        
        # Логирование
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="👢 Пользователь кикнут",
                description=f"Модератор: {ctx.author.mention}\nПользователь: {member.mention}\nПричина: {reason}\nДата: {ctx.message.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
                color=discord.Color.orange()
            )
            embed.set_footer(text="Shenята | TWITCH")
            await log_channel.send(embed=embed)
        
        await ctx.send(f"👢 {member.mention} кикнут. Причина: {reason}")
        
    except discord.Forbidden:
        await ctx.send("❌ У меня нет прав на кик пользователей!")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        return
    if isinstance(error, commands.CommandNotFound):
        return
    await ctx.send(f"Ошибка: {error}")
bot.run(TOKEN)