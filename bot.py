import discord
from discord.ext import commands
import datetime
from music_cog import MusicCog
import asyncio

from urllib import parse, request
from urllib.error import HTTPError
import re

def run_bot():
    TOKEN = 'MTA0MDE1OTM0MjQyNDUxMDQ3NA.Gg0M6R.Xddnip9BwcZpbE1ClwoBfmIinIQSFerGaoWKF4'
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix='!', description="Ayy lmaoisha", intents= intents)
    bot.remove_command("help")


    @bot.command()
    async def ping(ctx):
        await ctx.send('papino')

    @bot.command()
    async def info(ctx):
        embed = discord.Embed(title = f"{ctx.guild.name}",description="wtf is gogin gon",
                              timestamp=datetime.datetime.utcnow(), color=discord.Color.blue())
        embed.add_field(name = "EL server esta desde", value= f"{ctx.guild.created_at}")
        embed.add_field(name = "El capo", value= f"{ctx.guild.owner}")
        embed.add_field(name="Id del server", value=f"{ctx.guild.id}")
        embed.set_thumbnail(url = f"https://i.pinimg.com/736x/76/4d/ec/764dec1e7cb8818ce9729dc14c002c9f.jpg")
        await ctx.send(embed = embed)


    @bot.command()
    async def lolg(ctx, region : str, *, user):
        parseado = user.replace(" ", "+")
        url = 'http://www.leagueofgraphs.com/summoner/' + region + '/' + parseado
        await ctx.send(url)

    @bot.command()
    async def youtube(ctx, *, search):
        cantidad = search.split(' ')
        if cantidad[-1].isnumeric() and 0 < int(cantidad[-1]) < 10 :
            search = ' '.join(cantidad[:len(cantidad)-1])
            cantidad = int(cantidad[-1])
        else:
            cantidad = 1
        query_string = parse.urlencode({'search_query': search})
        url = 'http://www.youtube.com/results?'+ query_string
        client = request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        html_content = request.urlopen(client).read().decode()
        search_results = re.findall(r"watch\?v=(\S{11})", html_content)
        link = 'https://www.youtube.com/watch?v='
        for i in range(cantidad):
            await ctx.send(link + search_results[i])

    @bot.command(name = "help", aliases = ['h'])
    async def help(ctx):
        embed = discord.Embed(title = 'El prefijo es !', description="Esenciales\n!p(play) !l(leave) !c(clear) !q(queue) !s(skip) !d(delete)", color = discord.Color.dark_purple())
        await ctx.send(embed = embed)
        await ctx.message.delete()

    @bot.event
    async def on_ready():
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="A tu vieja"))
        await bot.add_cog(MusicCog(bot))
        commands = bot.get_cog('MusicCog')
        commands.queue_contorl.start()
        print('Funcionando papino')

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        commands = bot.get_cog('MusicCog')
        if error == HTTPError:
            if error == 403:
                print(error)
                commands.debug(ctx)





    '''@bot.event
    async def on_message(message):
        if message.author == bot.user:
            return
        print(message.embeds[0].to_dict())
        discord.embeds.Embed

        for embed in message.embeds:
            await message.channel.send(embed=embed)'''

    bot.run(TOKEN)
