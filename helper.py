import datetime
import json
import sqlite3
from contextlib import suppress
from functools import partial
from os import listdir
from time import sleep

import discord
from colorama import Fore, Style, init
from discord.ext import commands

json_data = json.load(open("config.json"))
init(autoreset=True)


def embed_builder(title: str, *, description: str = None, color: discord.Colour = discord.Colour.green()):
    """Создаёт :class:`discord.embed` с указанным цветом, заголовком и описанием
    
    Параметры
    ------------
    title: :class:`str`
        Заголовок эмбеда
    description: Optional[:class:`str`]
        Описание эмбеда
    color: Optional[:class:`discord.Colour`]
        Цвет эмеда, то есть полоса слева
    """
    return discord.Embed(title=title, description=description, color=color)


def database(command: str, *options, short: bool = True) -> list:
    """Делает запрос в базу данных
    
    Параметры
    ------------
    command: :class:`str`
        Команда на языке SQL
    *options:
        Значения для замены '?' в команде
    short: Optional[:class:`bool`]
        Сокращать ли возвращаемый массив
        
    Примеры
    -----------
        h.database("SELECT guild FROM users WHERE id = ?", ctx.author.id) -> 6

        h.database("SELECT guild FROM users WHERE id = ?", ctx.author.id, short=False) -> [(6,)]
    """
    db_filename = json_data["db"] # Получаем имя файла базы данных
    while True: # Необходимо для воизбежание ошибки "Database is locked"
        try:
            # Подключемся к базе данных и выполняем команду
            conn = sqlite3.connect(db_filename, timeout=1)
            cursor = conn.cursor()
            return_str = list(cursor.execute(command, options)) if options else list(cursor.execute(command))
            # Сохраняем изменения и отключаемся
            conn.commit()
            cursor.close()
            conn.close()
            if not short: # Если не сокращать - выходим
                # if command.startswith("SELECT"):
                #     Log.debug(return_str)
                return return_str
            if len(return_str) != 1: # Если несколько элементов - выходим
                # if command.startswith("SELECT"):
                #     Log.debug(return_str)
                return return_str
            try:
                if type(return_str[0]) == tuple and len(return_str[0]) == 1: # Если у нас вывод типа [(5,)] возвращаем только значение
                    return return_str[0][0]
                else: # Иначе, у нас вывод типа [(4, "Name")] или [4]
                    return return_str[0]
            except IndexError: # Если массив - пустой
                return return_str
        except sqlite3.OperationalError as e: # Избегаем "Database is locked", но сообщаем об ошибках
            Log.error(e)
            sleep(1)
            continue


class Profile:
    def __init__(self, id: int):
        self.id = id
        self.items = None
    
    def load(self):
        if not database("SELECT * FROM profile WHERE id = ?", self.id):
            database("INSERT INTO profile values (?, ?)", self.id, "[]")
        self.items = eval(database("SELECT items FROM profile WHERE id = ?", self.id))
    
    def save(self):
        database("UPDATE profile SET items=? WHERE id=?", str(self.items), self.id)
    
    def add(self, item: str):
        self.items.append(item)
        return self.items
    
    def remove(self, item: str):
        self.items.remove(item)
        return self.items
    
    def set(self, items: list):
        self.items = items
        return self.items
    
    def get(self):
        return self.items

    def clear(self):
        self.items = None

class Log:
    """Класс для создания и записи логов"""
    @staticmethod
    def log(content: str, *, code: str = "ok", logged: bool = True, color=Fore.WHITE, style=Style.NORMAL):
        """Создаёт лог

        Параметры
        ------------
        content: :class:`str`
            Тело лога
        code: Optional[:class:`str`]
            Код состояния лога
        logged: Optional[:class:`bool`]
            Сохранять ли лог в файл
        color: Optional
            Цвет сообщения в консоли. Тип - colorama.Fore.*
        style: Optional
            Стиль сообщения в консоли. Тип - colorama.Style.*
        """
        output = Log.__generate_output(content, code)
        print(f"{color}{style}{output}")
        if logged:
            Log.__to_txt(output)

    info = partial(log, code="info", color=Fore.BLUE, style=Style.BRIGHT)
    error = partial(log, code="error", color=Fore.RED, style=Style.BRIGHT)
    debug = partial(log, code="debug", color=Fore.YELLOW)
    command = partial(log, code="command", color=Fore.LIGHTGREEN_EX)

    '''@staticmethod # TODO Доделать
    async def discord(ctx: commands.Context, **kwargs):
        try:
            log_channel = ctx.guild.get_channel(json_data["debug_channel"])
            await log_channel.send(**kwargs)
        except Exception as e:
            Log.error(e, logged=False)'''

    @staticmethod
    def __to_txt(output):
        """Записывает лог в файл"""
        with open(f"logs/log_{datetime.date.today()}.txt", "a", encoding="UTF-8") as file:
            file.write("\n" + output)

    @staticmethod
    def __generate_output(message: str = None, code: str = "ok"):
        """Генерирует лог основываясь на теле и коде состояния"""
        return f"[{datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')}] [{code.upper()}]: {message}"

class MyBot(commands.Bot):
    """Основной класс бота

        Параметры
        ------------
        debug: :class:`bool`
            Находится ли бот в состоянии отладки. Влияет на поведение некоторых функций, например on_command_error
        help_cog_file: Optional[:class:`str`]
            Файл с когом с командой help. Стандартное значение - help.py
        have_cogs: Optional[:class:`bool`]
            Есть ли коги у бота. Стандартное значение - False
    """
    def __init__(self, *, debug: bool, help_cog_file: str = "help.py", have_cogs: bool = False):
        super().__init__(application_id=json_data["application_id"], intents=discord.Intents.all(), command_prefix=commands.when_mentioned_or(json_data['prefix']), case_insensitive=True, strip_after_prefix=True)
        self.debug = debug
        self.help_cog_file = help_cog_file
        self.have_cogs = have_cogs

    async def setup_hook(self):
        if not self.have_cogs: return
        # Получаем все файлы с когами
        for cog in listdir("cogs"):
            with suppress(commands.errors.NoEntryPointError):
                if cog.endswith(".py"):
                    try:
                        # Если мы не удалили команду вначале и подгрузили ког с командой help, то убираем стандартный хелп
                        if cog == self.help_cog_file and not self.remove_help:
                            self.remove_command("help")
                        # Загружаем ког
                        await self.load_extension(f"cogs.{cog[:-3]}")
                        Log.info(f"Loaded cog: cogs.{cog[:-3]}")
                    except Exception as e:
                        # На случай хуйни
                        Log.error(f"cog cogs.{cog[:-3]} failed to load due to error: {e}.")
    
    def get_all_my_voices(self):
        """Возвращает все голосовые каналы в зоне 'Видимости'"""
        for i in self.get_all_channels():
            if type(i) in (discord.VoiceChannel, discord.StageChannel):
                yield i
    
    def get_all_my_texts(self):
        """Возвращает все голосовые каналы в зоне 'Видимости'"""
        for i in self.get_all_channels():
            if type(i) in (discord.TextChannel, discord.ForumChannel, discord.Thread):
                yield i
    
    async def on_ready(self):
        Log.log(f"Logged in as {self.user}(ID: {self.user.id})", code="ready", color=Fore.MAGENTA, style=Style.BRIGHT)
    
    async def on_command_error(self, ctx: commands.Context, exception: Exception):
        if self.debug: return await super().on_command_error(ctx, exception) # Если включён режим отладки - игнорируем эту команду
        if isinstance(exception, commands.MissingPermissions):
            # При недостатке прав
            await ctx.send("У вас недостаточно прав для выполнения данного действия", delete_after=json_data["delete_after"]["error"])
            return await ctx.message.delete()
        '''if isinstance(exception, commands.CommandNotFound):
            # При остутсвии команды
            await ctx.send(
                "Такой команды не существует :disappointed_relieved:",
                delete_after=h.json_data["delete_after"]["error"]
            )
            return await ctx.message.delete(delay=h.json_data["delete_after"]["error"])'''
        # При любой другой ошибке создаём лог и выводим сообщение об ошибке в чат
        await Log.error(f"Произошла ошибка {exception.__class__.__name__}{exception.args} при выполнении команды {ctx.command}")
        await ctx.send(f"Браво, вы победили меня. Скажите модераторам, что у меня {exception.__class__.__name__}{exception.args} в {datetime.datetime.now()}")
        raise exception
    
    def run(self):
        super().run(json_data["token"])


def __admin_check(ctx: commands.Context, *_):
    #проходим по каждой роли и проверяем есть ли она в списке админ-ролец
    for i in ctx.author.roles:
        if i in json_data["admin_roles"]:
            return True
    return False


def is_admin():
    return commands.check(__admin_check)