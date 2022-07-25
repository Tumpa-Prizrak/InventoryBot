import helper as h
import discord
from discord.ext import commands

bot = commands.Bot(application_id=h.json_data["application_id"], intents=discord.Intents.all(), command_prefix=commands.when_mentioned_or(h.json_data['prefix']), case_insensitive=True, strip_after_prefix=True)
bot.remove_command("help")

@bot.command(name="list", brief="Просмотр инвентаря пользователя", usage="[Пользователь]")
async def comm_list(ctx: commands.Context, memb: discord.Member = None):
    if memb is None:
        memb = ctx.author
    profile = h.Profile(memb.id)
    profile.load()
    if profile.get() is []:
        await ctx.send(f"Инвентарь пользователя {memb.mention}:\n*Пусто*")
    else:
        await ctx.send(f"Инвентарь пользователя {memb.mention}:\n" + "\n".join(profile.get()))

@bot.command(name="add", brief="Добавляет предмет из инвентаря пользователя", usage="<Пользователь> <Название предмета>")
@h.is_admin()
async def comm_add(ctx: commands.Context, memb: discord.Member, *, obj: str):
    profile = h.Profile(memb.id)
    profile.load()
    profile.add(obj)
    profile.save()
    await ctx.send(f"Добавлен предмет {obj}")

@bot.command(name="remove", brief="Удаляет предмет из инвентаря пользователя", usage="<Пользователь>")
@h.is_admin()
async def comm_remove(ctx: commands.Context, memb: discord.Member):
    profile = h.Profile(memb.id)
    await ctx.send("Выберете предмет из списка: " + profile.get())
    mess: discord.Message = bot.wait_for("message", check=lambda msg: msg.author.id == ctx.author.id and msg.content in profile.get())
    profile.remove(mess.content)
    profile.save()

@commands.command(name="help", brief="Просмотреть список комманд", usage="")
async def comm_help(self, ctx: commands.Context):
    commands = list(map(lambda x: f'{h.json_data["prefix"]}{x.name} {x.usage} - {x.brief}', self.client.commands)) 
    h.Log.debug(commands)
    await ctx.send("**Команды:**\n{}".format("\n".join(map(lambda x: f'{h.json_data["prefix"]}{x.name} {x.usage} - {x.brief}', self.client.commands))))

try:
    bot.run(h.json_data["token"])
except __import__("aiohttp").ClientConnectionError: 
    h.error("Возможно, вы не в сети - проверьте ваше интернет соеденение и попробуйте ещё раз.")