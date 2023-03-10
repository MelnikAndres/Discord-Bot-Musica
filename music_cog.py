import asyncio

import discord
from discord.ext import commands, tasks
from youtube_dl import YoutubeDL

import time

REACTION = 0
PLAY = 1
SKIP = 2
QUEUE = 3
CLEAR = 4
LEAVE = 5
DELETE = 6
BB = 7
CUSTOM = 8


class FakeMessage:
    def __init__(self):
        pass
    async def delete(self):
        pass

class FakeCtx:
    def __init__(self, author, real):
        self.author = author
        self.real = real
        self.message = FakeMessage()

    async def send(self, embed):
        return await self.real.send(embed = embed)


class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.is_playing = False
        self.is_paused = False

        self.music_queue = []
        self.YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist': 'True'}
        self.FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options':'-vn'}
        self.vc = None
        self.working = False
        self.react_save = []
        self.songs_id = []
        self.cancel = False
        self.command_queue = []

    def search_yt(self, item):
        with YoutubeDL(self.YDL_OPTIONS) as ydl:
            try:
                if 'youtube.com' in item:
                    info = ydl.extract_info(item[0:44], download=False)
                else:
                    info = ydl.extract_info("ytsearch:%s" % item, download=False)['entries'][0]

            except Exception:
                return False
        print(info['formats'][0]['url'])
        return {'source': info['formats'][0]['url'], 'title': info['title'], 'id': info['id'], 'busqueda': item}


    def _play_next(self,error):

        coro = self.play_next(error = error)
        fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
        try:
            fut.result()
        except:
            # an error happened sending the message
            pass

    async def manage_queue(self):
        self.music_queue.pop(0)
        self.songs_id.pop(0)
        await self.react_save[0].clear()
        self.react_save.pop(0)
        await self.react_save[0].clear()
        self.react_save.pop(0)

    def play_ffmpeg(self, url, intentos):
        try:
            self.vc.play(
                discord.FFmpegPCMAudio(url, **self.FFMPEG_OPTIONS, executable="D:/Programas/ffmpeg/bin/ffmpeg.exe"),
                after=self._play_next)
        except:
            if intentos < 4:
                print("Reintentando musica...")
                time.sleep(0.5)
                self.vc.cleanup()
                self.play_ffmpeg(url, intentos + 1)

    async def play_next(self, error = None):
        if len(self.music_queue) > 1:
            if not error:
                await self.manage_queue()
            else:
                print(f"El error es:\n{error}")
            self.is_playing = True
            m_url = self.music_queue[0][0]['source']
            self.play_ffmpeg(m_url, 0)
        else:
            if len(self.music_queue) == 1:
                await self.manage_queue()
            self.is_playing = False

    async def play_music(self, ctx):
        self.is_playing = True
        m_url = self.music_queue[0][0]['source']

        if self.vc == None or not self.vc.is_connected():
            self.vc = await self.music_queue[0][1].connect()

            if self.vc == None:
                embed = discord.Embed(title="Error",description = 'No me pude conectar al canal',color=discord.Color.yellow())
                await ctx.send(embed =  embed)
                return
        else:
            await self.vc.move_to(self.music_queue[0][1])

        self.play_ffmpeg(m_url, 0)


    @commands.Cog.listener(name = 'on_reaction_add')
    async def on_reaction_add(self, reaction, user):
        if self.command_queue:
            self.command_queue.append([REACTION, reaction, user])
            return
        if user == self.bot.user:
            self.react_save.append(reaction)
            if len(self.songs_id) == 0 or reaction.message.id not in(self.songs_id):
                self.songs_id.append(reaction.message.id)
            return
        if reaction.emoji == self.react_save[0].emoji :
            await self.pause(None)
        elif reaction.emoji == self.react_save[1].emoji :
            for i, song_id in enumerate(self.songs_id):
                if song_id == reaction.message.id:
                    await self.skip(None, str(i), author = user, channel = reaction.message.channel)
        await reaction.remove(user)


    @commands.command(name = 'play', aliases = ['p', 'playing'], help= 'Pone la musica de youtube')
    async def play(self,ctx,*args):
        if self.command_queue:
            self.command_queue.append([PLAY,ctx,*args])
            return
        if not self.working:
            self.working = True
            await self._play(ctx, *args)
        else:
            await asyncio.sleep(0.2)
            await self.play(ctx, *args)
        self.working = False

    async def _play(self, ctx, *args):
        query = ' '.join(args)
        voice_channel = ctx.author.voice
        if voice_channel is None:
            embed = discord.Embed(title="Error", description = 'No estas conectado a ningun canal?',color=discord.Color.yellow())
            await ctx.send(embed = embed)
        elif self.is_paused:
            self.vc.resume()
        else:
            voice_channel = voice_channel.channel
            song = self.search_yt(query)

            if not song:
                embed = discord.Embed(title="No encontrada",description=f'{query}\n No arroja ningun resultado',color=discord.Color.yellow())
                await ctx.send(embed = embed)
                return
            self.music_queue.append([song, voice_channel])
            id = song['id']
            title = song['title']
            url = 'https://www.youtube.com/watch?v=' + id
            embed = discord.Embed(title=f"Encolado #{len(self.music_queue)-1}", description= f'[{title}]({url})\n\nAgregado por {ctx.author.mention}', color=discord.Color.red())
            embed.set_thumbnail(url=f"https://i.ytimg.com/vi/{id}/maxresdefault.jpg")
            mensaje = await ctx.send(embed = embed)
            await mensaje.add_reaction("⏯")
            await mensaje.add_reaction("⏩")
            if self.is_playing == False:
                await self.play_music(ctx)
        await ctx.message.delete()

    @commands.command(name = 'pause', help= "pausa la cancion papino")
    async def pause(self,ctx,*args):
        if self.is_playing:
            self.is_playing = False
            self.is_paused = True
            self.vc.pause()
        elif self.is_paused:
            self.is_playing = True
            self.is_paused = False
            self.vc.resume()
        if ctx:
            await ctx.message.delete()

    @commands.command(name = 'resume', aliases =['r'], help= "suena denuevo papino")
    async def resume(self, ctx, *args):
        if self.is_paused:
            self.is_playing = True
            self.is_paused = False
            self.vc.resume()
        if ctx:
            await ctx.message.delete()

    @commands.command(name = 'skip', aliases = ['s'], help = 'skippea papino')
    async def skip(self, ctx, *args, author = None, channel = None):
        if self.command_queue:
            self.command_queue.append([SKIP, ctx, *args, author, channel])
            return

        if len(self.music_queue) == 0:
            embed = discord.Embed(title = "Error",
                                  description = "No se esta reproduciendo musica actualmente\n"
                                                "Podes agregar musica con !p",
                                  color = discord.Color.yellow())
            await ctx.send(embed = embed)
            try:
                await ctx.message.delete()
            except:
                pass
            return

        if len(args) == 0:
            jump = '1'
        else:
            jump = args[0]
        if jump.isnumeric():
            jump = int(jump)
            if len(self.music_queue) == 1 or jump == 0:
                song = self.music_queue[0][0]
                url = 'https://www.youtube.com/watch?v=' + song['id']
                if ctx:
                    texto = f'{ctx.author.mention} Skipeó la cancion\n[{song["title"]}]({url})'
                else:
                    texto = f'{author.mention} Skipeó la cancion\n[{song["title"]}]({url})'
            else:
                for i in range(jump-1):
                    await self.manage_queue()
                song = self.music_queue[1][0]
                url = 'https://www.youtube.com/watch?v=' + song['id']
                if ctx:
                    texto = f'{ctx.author.mention} Skipeó hasta\n[{song["title"]}]({url})\nPosicion #{jump}'
                else:
                    texto = f'{author.mention} Skipeó hasta\n[{song["title"]}]({url})\nPosicion #{jump}'

            embed = discord.Embed(title = 'Skip', description=texto, color = discord.Color.blue())
            if channel:
                await channel.send(embed=embed)
            else:
                await ctx.send(embed=embed)

        if ctx:
            try:
                await ctx.message.delete()
            except:
                pass
        self.vc.stop()

    @commands.command(name = 'queue', aliases = ['q'], help= 'muestra la cola papino goloso')
    async def queue(self, ctx):
        if self.command_queue:
            self.command_queue.append([QUEUE, ctx])
            return
        if len(self.music_queue) == 0:
            embed = discord.Embed(title = "Cola Vacia", description="Agrega musica con el comando !p", color= discord.Color.yellow())
            await ctx.send(embed = embed)

        for i in range(0, len(self.music_queue)):
            if i > 6:
                break
            id = self.music_queue[i][0]['id']
            title = self.music_queue[i][0]['title']
            url = 'https://www.youtube.com/watch?v=' + id
            if i == 0:
                titulo = "Escuchando"
                color = discord.Color.green()
            else:
                titulo = f"Posicion #{i}"
                color = discord.Color.blue()
            embed = discord.Embed(title=titulo,description=  f'[{title}]({url})\n\nAgregado por {ctx.author.mention}', color=color)
            embed.set_thumbnail(url=f"https://i.ytimg.com/vi/{id}/maxresdefault.jpg")

            mensaje = await ctx.send(embed =  embed)
            self.songs_id[i] = mensaje.id
            await self.react_save[0].clear()
            self.react_save.pop(0)
            await self.react_save[0].clear()
            self.react_save.pop(0)
            await mensaje.add_reaction("⏯")
            await mensaje.add_reaction("⏩")

        if ctx:
            await ctx.message.delete()



    @commands.command(name = 'clear', aliases = ['c', 'bin'], help = 'borra la cola papino')
    async def clear(self, ctx, *args):
        if self.command_queue:
            self.command_queue.append([CLEAR, ctx, *args])
            return
        if len(self.music_queue) <= 1:
            embed = discord.Embed(title = "Cola Vacia", description="Agrega musica con el comando !p", color= discord.Color.yellow())
            await ctx.send(embed = embed)
            await ctx.message.delete()
            return

        for i in range(1, len(self.music_queue)):
            await self.react_save[2].clear()
            self.react_save.pop(2)
            await self.react_save[2].clear()
            self.react_save.pop(2)
            self.music_queue.pop(1)
            self.songs_id.pop(1)

        embed = discord.Embed(title="Cola Borrada",description=  f'{ctx.author.mention} borró la cola actual', color=discord.Color.light_gray())
        await ctx.send(embed = embed)
        await ctx.message.delete()

    @commands.command(name = 'leave', aliases = ['disconnect', 'l'], help ='me voy papino')
    async def leave(self, ctx):
        if self.command_queue:
            self.command_queue.append([LEAVE, ctx])
            return
        await self.vc.disconnect()
        await self.skip(ctx, str(len(self.music_queue)+1))
        self.is_playing = False
        self.is_paused = False
        try:
            await ctx.message.delete()
        except Exception:
            pass

    @commands.command(name = 'delete', aliases = ['d'], help= 'borra una papino')
    async def delete(self,ctx, *args):
        if self.command_queue:
            self.command_queue.append([DELETE, ctx, *args])
            return
        if not args:
            await ctx.message.delete()
        elif args[0].isnumeric():
            index = int(args[0])
            if index >= len(self.music_queue):
                await ctx.message.delete()
                embed = discord.Embed(title='Error',
                                      description=f'{" ".join(args)}\nNo es una posicion valida',
                                      color=discord.Color.yellow())
                await ctx.send(embed = embed)
                return
            song = self.music_queue[index][0]
            url = 'https://www.youtube.com/watch?v=' + song['id']
            embed = discord.Embed(title= 'Borrado',
                                  description=f'[{song["title"]}]({url})\nFue borrado por {ctx.author.mention}',
                                  color = discord.Color.light_gray())
            await self.react_save[2*index].clear()
            self.react_save.pop(2*index)
            await self.react_save[2*index].clear()
            self.react_save.pop(2*index)
            self.music_queue.pop(index)
            self.songs_id.pop(index)
            await ctx.send(embed = embed)
        else:
            query = ' '.join(args)
            for i, elemento in enumerate(self.music_queue):
                if elemento[0]['busqueda'] == query:
                    await self.delete(ctx, str(i))
                    return
            embed = discord.Embed(title='Error',
                                    description=f'{" ".join(args)}\nNo es una busqueda previa',
                                    color=discord.Color.yellow())
            await ctx.send(embed=embed)
        try:
            await ctx.message.delete()
        except:
            pass

    @commands.command(name="bb", aliases = ['conejo','badbunny'], help= 'bad bunny baby')
    async def bb(self, ctx, *args):
        if self.command_queue:
            self.command_queue.append([BB, ctx, *args])
            return
        with open("bad_bunny.txt") as bad:
            for cancion in bad:
                cancion = cancion.rstrip()
                await self.play(FakeCtx(ctx.author, ctx), cancion)
        await ctx.message.delete()
        embed = discord.Embed(title = 'Bad Bunny Baby',
                              description = 'Conejito malo pa todas las cachorras',
                              color = discord.Color.orange())
        await ctx.send(embed = embed)

    @commands.command(name="custom", help='bad bunny baby')
    async def custom(self, ctx):
        if self.command_queue:
            self.command_queue.append([CUSTOM, ctx])
            return
        texto = (await ctx.message.attachments[0].read()).decode("utf-8")
        texto = texto.replace("\r\n", "\n")
        texto = texto.replace("\n", "$")
        texto = texto.split("$")
        if len(texto) > 0:
            for cancion in texto:
                cancion = cancion.rstrip()
                await self.play(FakeCtx(ctx.author, ctx), cancion)

        await ctx.message.delete()
        embed = discord.Embed(title='Custom Playlist',
                              description=f'Playlist cargada por {ctx.author.mention}',
                              color=discord.Color.orange())
        await ctx.send(embed=embed)

    @commands.command(name="debug", help='debugea')
    async def debug(self, ctx):
        try:
            self.is_playing = False
            self.is_paused = False

            self.music_queue = []
            await self.vc.move_to(ctx.author.voice.channel)
            await self.vc.disconnect()
            self.vc = await ctx.author.voice.channel.connect()
            self.react_save = []
            self.songs_id = []
            self.command_queue = []
        except:
            pass
        finally:
            await ctx.message.delete()

    @commands.command(name="cancel", help='cancela comandos en curso')
    async def cancel(self, ctx):
        self.command_queue = []

    @tasks.loop(seconds=0.5)
    async def queue_contorl(self):
        if self.command_queue:
            values = self.command_queue.pop(0)
            if values[0] == REACTION:
                await self.on_reaction_add(values[1], values[2])

            elif values[0] == PLAY:
                await self.play(values[1],values[2])

            elif values[0] == SKIP:
                await self.skip(values[1], values[2], values[3], values[4])

            elif values[0] == QUEUE:
                await self.queue(values[1])

            elif values[0] == CLEAR:
                await self.clear(values[1], values[2])

            elif values[0] == LEAVE:
                await self.leave(values[1])

            elif values[0] == DELETE:
                await self.delete(values[1], values[2])

            elif values[0] == BB:
                await self.bb(values[1], values[2])

            elif values[0] == CUSTOM:
                await self.custom(values[1])

