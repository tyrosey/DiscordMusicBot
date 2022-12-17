##############################################################
#
# Discord Bot 'Tyborg' main script written in Python, with 
# a music bot written in discord.py using youtube-dl.
#
# Music Bot source code -- Copyright (c) 2019 Valentin B.
#
#
##############################################################

import discord
import os
import asyncio
import functools
import itertools
import math
import random
import urllib
import youtube_dl
from async_timeout import timeout
from discord.ext import commands
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from googlesearch import search
from random import randint
from datetime import datetime

load_dotenv()


token = os.getenv("DISCORD_TOKEN")
roast_path = os.getenv("ROAST_PATH")
jokes_path = os.getenv("JOKES_PATH")
help_path = os.getenv("HELP_PATH")
log_path = os.getenv("LOG_PATH")
badWords = os.getenv("BAD_WORDS")


# random variable instantiations
mockMeme = "https://i.kym-cdn.com/entries/icons/original/000/022/940/mockingspongebobbb.jpg"
helpPic = "https://st.depositphotos.com/1431107/4033/v/950/depositphotos_40334707-stock-illustration-vector-help-sign.jpg"
bot = discord.Client()                                                  

# Silence useless bug reports messages for music
youtube_dl.utils.bug_reports_message = lambda: ''


# function for logging information to the bot's log file when the bot is pinged
async def logInfo(ctx, commandPrompt):
    now = datetime.now()                                                    
    dateTime = now.strftime("%b-%d-%Y %H:%M:%S ")                           
    author = str(ctx.message.author)                                        
    server = str(ctx.message.guild.name)                                    
    messageContent = str(ctx.message.content)                               
    messageContent = messageContent.replace("<@982907926199025724>", "").strip()    
    userName = "none"                                                   
    
    temp = messageContent.split()                                       
    for word in temp:                                                   
        if word.startswith("<@"):                                       
            userID = word                                               
            messageContent = messageContent.replace(userID, "")         
            messageContent = messageContent.replace("  ", " ").strip()  
            
            if ";" in messageContent:                                   
                messageContent = messageContent.split(";", 1)           
                messageContent = messageContent[1].strip()                       
            print("\n\n\n" + messageContent)
            userID = userID.replace("<@", "")                   
            userID = userID.replace(">", "")                    
            userID = userID.replace("!", "")                    
            userID = int(userID)                                
            
            userName = await bot.fetch_user(userID)             
            userName = str(userName)                            
    
    if ":" in messageContent:                                   
        messageContent = messageContent.split(":", 1)           
        messageContent = messageContent[1].strip()                                   
        print("\n\n\n" + messageContent)

    logFile = open(log_path, "a")                              
    logFile.write(f"{dateTime + '  Server: ' + server : <50}" + f"{'Author: ' + author : <35}" + f"{'   Command: ' + commandPrompt : <25}" + f"{'   Target(user): ' + userName : <40}" + '   Content: "' + messageContent + '"\n')   # organizing and writing to log file
    logFile.close()                                             



##############################################################
#                                                            #
#   MUSIC BOT -- (edited) SOURCE CODE IMPLEMENTATION BELOW   #
#                                                            #
##############################################################

class VoiceError(Exception):
    pass


class YTDLError(Exception):
    pass


class YTDLSource(discord.PCMVolumeTransformer):
    YTDL_OPTIONS = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
    }

    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn',
    }

    ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)

    def __init__(self, ctx: commands.Context, source: discord.FFmpegPCMAudio, *, data: dict, volume: float = 0.5):
        super().__init__(source, volume)

        self.requester = ctx.author
        self.channel = ctx.channel
        self.data = data

        self.uploader = data.get('uploader')
        self.uploader_url = data.get('uploader_url')
        date = data.get('upload_date')
        self.upload_date = date[6:8] + '.' + date[4:6] + '.' + date[0:4]
        self.title = data.get('title')
        self.thumbnail = data.get('thumbnail')
        self.description = data.get('description')
        self.duration = self.parse_duration(int(data.get('duration')))
        self.tags = data.get('tags')
        self.url = data.get('webpage_url')
        self.views = data.get('view_count')
        self.likes = data.get('like_count')
        self.dislikes = data.get('dislike_count')
        self.stream_url = data.get('url')

    def __str__(self):
        return '**{0.title}** by **{0.uploader}**'.format(self)

    @classmethod
    async def create_source(cls, ctx: commands.Context, search: str, *, loop: asyncio.BaseEventLoop = None):
        loop = loop or asyncio.get_event_loop()

        partial = functools.partial(cls.ytdl.extract_info, search, download=False, process=False)
        data = await loop.run_in_executor(None, partial)

        if data is None:
            raise YTDLError('Couldn\'t find anything that matches `{}`'.format(search))

        if 'entries' not in data:
            process_info = data
        else:
            process_info = None
            for entry in data['entries']:
                if entry:
                    process_info = entry
                    break

            if process_info is None:
                raise YTDLError('Couldn\'t find anything that matches `{}`'.format(search))

        webpage_url = process_info['webpage_url']
        partial = functools.partial(cls.ytdl.extract_info, webpage_url, download=False)
        processed_info = await loop.run_in_executor(None, partial)

        if processed_info is None:
            raise YTDLError('Couldn\'t fetch `{}`'.format(webpage_url))

        if 'entries' not in processed_info:
            info = processed_info
        else:
            info = None
            while info is None:
                try:
                    info = processed_info['entries'].pop(0)
                except IndexError:
                    raise YTDLError('Couldn\'t retrieve any matches for `{}`'.format(webpage_url))

        return cls(ctx, discord.FFmpegPCMAudio(info['url'], **cls.FFMPEG_OPTIONS), data=info)

    @staticmethod
    def parse_duration(duration: int):
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        duration = []
        if days > 0:
            duration.append('{} days'.format(days))
        if hours > 0:
            duration.append('{} hours'.format(hours))
        if minutes > 0:
            duration.append('{} minutes'.format(minutes))
        if seconds > 0:
            duration.append('{} seconds'.format(seconds))

        return ', '.join(duration)


class Song:
    __slots__ = ('source', 'requester')

    def __init__(self, source: YTDLSource):
        self.source = source
        self.requester = source.requester

    def create_embed(self):
        embed = (discord.Embed(title='Now playing',
                               description='```css\n{0.source.title}\n```'.format(self),
                               color=discord.Color.blurple())
                 .add_field(name='Duration', value=self.source.duration)
                 .add_field(name='Requested by', value=self.requester.mention)
                 .add_field(name='Uploader', value='[{0.source.uploader}]({0.source.uploader_url})'.format(self))
                 .add_field(name='URL', value='[Click]({0.source.url})'.format(self))
                 .set_thumbnail(url=self.source.thumbnail))

        return embed


class SongQueue(asyncio.Queue):
    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        else:
            return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    def clear(self):
        self._queue.clear()

    def shuffle(self):
        random.shuffle(self._queue)

    def remove(self, index: int):
        del self._queue[index]


class VoiceState:
    def __init__(self, bot: commands.Bot, ctx: commands.Context):
        self.bot = bot
        self._ctx = ctx

        self.current = None
        self.voice = None
        self.next = asyncio.Event()
        self.songs = SongQueue()

        self._loop = False
        self._volume = 0.5
        self.skip_votes = set()

        self.audio_player = bot.loop.create_task(self.audio_player_task())

    def __str__(self):
        return '**{0.title}** by **{0.uploader}**'.format(self)


    def __del__(self):
        self.audio_player.cancel()

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, value: bool):
        self._loop = value

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value: float):
        self._volume = value

    @property
    def is_playing(self):
        return self.voice and self.current

    async def audio_player_task(self):
        while True:
            self.next.clear()

            if not self.loop:
                # Try to get the next song within 3 minutes.
                # If no song will be added to the queue in time,
                # the player will disconnect due to performance
                # reasons.
                try:
                    async with timeout(180):  # 3 minutes
                        self.current = await self.songs.get()
                except asyncio.TimeoutError:
                    self.bot.loop.create_task(self.stop())
                    return

            self.current.source.volume = self._volume
            self.voice.play(self.current.source, after=self.play_next_song)
            await self.current.source.channel.send(embed=self.current.create_embed())

            await self.next.wait()

    def play_next_song(self, error=None):
        if error:
            raise VoiceError(str(error))

        self.next.set()

    def skip(self):
        self.skip_votes.clear()

        if self.is_playing:
            self.voice.stop()

    async def stop(self):
        self.songs.clear()

        if self.voice:
            await self.voice.disconnect()
            self.voice = None


class Commands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_states = {}

    def get_voice_state(self, ctx: commands.Context):
        state = self.voice_states.get(ctx.guild.id)
        if not state:
            state = VoiceState(self.bot, ctx)
            self.voice_states[ctx.guild.id] = state

        return state

    def cog_unload(self):
        for state in self.voice_states.values():
            self.bot.loop.create_task(state.stop())

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage('This command can\'t be used in DM channels.')

        return True

    async def cog_before_invoke(self, ctx: commands.Context):
        ctx.voice_state = self.get_voice_state(ctx)

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        await ctx.send('An error occurred: {}'.format(str(error)))


    # JOIN - allows the bot to join the voice channel of whoever requested
    @commands.command(name='join', invoke_without_subcommand=True)
    async def _join(self, ctx: commands.Context):
        commandPrompt = "%join"
        await logInfo(ctx,commandPrompt)

        destination = ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            return

        ctx.voice_state.voice = await destination.connect()


    # LEAVE -- clears the queue and makes bot leave voice channel
    @commands.command(name='leave', aliases=['disconnect'])
    async def _leave(self, ctx: commands.Context):
        commandPrompt = "%leave"
        await logInfo(ctx,commandPrompt)

        if not ctx.voice_state.voice:
            return await ctx.send('Not connected to any voice channel.')

        await ctx.voice_state.stop()
        del self.voice_states[ctx.guild.id]


    # VOLUME -- allows players to set the volume of the music
    @commands.command(name='volume')
    async def _volume(self, ctx: commands.Context, *, volume: int):
        commandPrompt = "%volume"
        await logInfo(ctx,commandPrompt)

        if not ctx.voice_state.is_playing:
            return await ctx.send('Nothing being played at the moment.')

        if 0 > volume > 100:
            return await ctx.send('Volume must be between 0 and 100')

        ctx.voice_state.volume = volume / 100
        await ctx.send('Volume of the player set to {}%'.format(volume))


    # NOW -- displays info about the current song
    @commands.command(name='now', aliases=['current', 'playing'])
    async def _now(self, ctx: commands.Context):
        commandPrompt = "%now"
        await logInfo(ctx,commandPrompt)

        await ctx.send(embed=ctx.voice_state.current.create_embed())


    # PAUSE -- pauses the song currently playing
    @commands.command(name='pause')
    async def _pause(self, ctx: commands.Context):
        commandPrompt = "%pause"
        await logInfo(ctx,commandPrompt)

        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_playing():
            ctx.voice_state.voice.pause()
            await ctx.message.add_reaction('⏯')
 

    # RESUME -- resumes playing the currently paused song
    @commands.command(name='resume')
    async def _resume(self, ctx: commands.Context):
        commandPrompt = "%resume"
        await logInfo(ctx,commandPrompt)

        if ctx.voice_state.is_playing and not ctx.voice_state.voice.is_playing():
            ctx.voice_state.voice.resume()
            await ctx.message.add_reaction('⏯')


    # EMPTY -- empties the queue
    @commands.command(name='empty')
    async def _empty(self, ctx: commands.Context):
        commandPrompt = "%empty"
        await logInfo(ctx,commandPrompt)

        ctx.voice_state.songs.clear()
        await ctx.send("Queue has been emptied! Add some more songs!")


    # SKIP -- skips to next song in queue
    @commands.command(name='skip')
    async def _skip(self, ctx: commands.Context):
        commandPrompt = "%skip"
        await logInfo(ctx,commandPrompt)

        if  len(ctx.voice_state.songs) == 0:
            await ctx.message.add_reaction('⏭')
            ctx.voice_state.skip()
            return await ctx.send('The queue is empty! Add some songs!')
        
        else:
            await ctx.send('Playing next song in queue.')
            await ctx.message.add_reaction('⏭')
            ctx.voice_state.skip()
            ctx.voice_state.voice.resume()

    
    # QUEUE -- displays embed of all songs currently in the queue
    @commands.command(name='queue')
    async def _queue(self, ctx: commands.Context, *, page: int = 1):
        commandPrompt = "%queue"
        await logInfo(ctx,commandPrompt)
    
        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Queue is empty ):')

        items_per_page = 10
        pages = math.ceil(len(ctx.voice_state.songs) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue = ''
        for i, song in enumerate(ctx.voice_state.songs[start:end], start=start):
            queue += '`{0}.` [**{1.source.title}**]({1.source.url})\n'.format(i + 1, song)

        embed = (discord.Embed(description='**{} tracks:**\n\n{}'.format(len(ctx.voice_state.songs), queue))
                 .set_footer(text='Viewing page {}/{}'.format(page, pages)))
        await ctx.send(embed=embed)


    # SHUFFLE -- shuffles songs in the queue 
    @commands.command(name='shuffle')
    async def _shuffle(self, ctx: commands.Context):
        commandPrompt = "%shuffle"
        await logInfo(ctx,commandPrompt)

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        ctx.voice_state.songs.shuffle()
        await ctx.message.add_reaction('✅')
        await ctx.send("Queue has been shuffled!")
        


    # REMOVE -- removes a song from the queue at a given index
    @commands.command(name='remove')
    async def _remove(self, ctx: commands.Context, index: int):
        commandPrompt = "%remove"
        await logInfo(ctx,commandPrompt)
        
        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        ctx.voice_state.songs.remove(index - 1)
        await ctx.message.add_reaction('✅')
        await ctx.send("Song removed!")


    # LOOP -- will repeat the current song until turned off. DISABLED CURRENTLY.
#    @commands.command(name='loop')
#    async def _loop(self, ctx: commands.Context):

#        if not ctx.voice_state.is_playing:
#            return await ctx.send('Nothing being played at the moment.')

#        ctx.voice_state.loop = not ctx.voice_state.loop
#        await ctx.message.add_reaction('✅')


    # PLAY -- plays a song. Can give URL or just name and artist
    @commands.command(name='play', aliases=['add'])
    async def _play(self, ctx: commands.Context, *, search: str):
        
        if not ctx.voice_state.voice:
            await ctx.invoke(self._join)
            entranceSong = "https://www.youtube.com/watch?v=UfOKDqKXzS8"
            entranceSource = await YTDLSource.create_source(ctx, entranceSong, loop=self.bot.loop)
            entrySong = Song(entranceSource)
            await ctx.send("Joining now! Your requested song will play shortly.")
            await ctx.voice_state.songs.put(entrySong)
            
        async with ctx.typing():
            try:
                source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop)              
            except YTDLError as e:
                await ctx.send('An error occurred while processing this request: {}'.format(str(e)))
            else:
                song = Song(source)
                await ctx.voice_state.songs.put(song)
                await ctx.send('Added to queue {}'.format(str(source)))
        commandPrompt = "%play"
        await logInfo(ctx,commandPrompt)

    @_join.before_invoke
    @_play.before_invoke
    
    
    async def ensure_voice_state(self, ctx: commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise commands.CommandError('You are not connected to any voice channel.')

        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                raise commands.CommandError('Bot is already in a voice channel.')


#########################################################################
#                                                                       #
#   TYBORG BOT -- NON-MUSIC BOT CODE IMPLEMENTATIONS / COMMANDS BELOW   #
#                                                                       #
#########################################################################

    
    # COMMANDS -- gives embed list of all commands
    @commands.command(name='commands')
    async def _commands(self, ctx):
        commandPrompt = "%commands"                         
        f = open(help_path, 'r')                  
        info = f.read()                                
        f.close()                                       

        embedVar = discord.Embed(title = "Tyborg Command Information", description = info, color = 0x00ff00)    # organize embedded message
        embedVar.set_thumbnail(url = helpPic)           
        await ctx.send(embed=embedVar)                  
        await logInfo(ctx,commandPrompt)



    # HELLO -- gives a hello message
    @commands.command(name='hello')
    async def _hello(self, ctx: commands.Context):
        commandPrompt = "%hello"
        await ctx.send("What's up! (:")
        await logInfo(ctx,commandPrompt)

    
    # JOKE -- tells a joke
    @commands.command(name='joke')
    async def _joke(self, ctx: commands.Context):   

        commandPrompt = "/joke"                      
        jokeCount = randint(0,138)                   
        f = open(jokes_path, 'r')              
        jokeFile = f.readlines()                    
        joke = str(jokeFile[jokeCount])             
        f.close()                                   
        
        await ctx.send(joke)                        
        await logInfo(ctx,commandPrompt)            
    
    
    # ROAST -- Roasts a user
    @commands.command(name='roast')
    async def _roast(self, ctx, user : discord.Member):   
        commandPrompt = "%roast"                        
        
        if user.mention:
            pinged = user.mention                           
            pinged = pinged.replace("<@", "")                     
            pinged = pinged.replace(">", "")                
            pinged = pinged.replace("!", "")                
            pinged = int(pinged)                            
        else:
            roastCount = 0
        
        if pinged == 672509068174295052:                
            roastCount = 1                              
        elif pinged == 929071676728176733:              
            roastCount = 2                              
        elif pinged == 337081233437622281:              
            roastCount = randint(3,5)                  
        else:                                           
            roastCount = randint(6,391)                  
        f = open(roast_path, 'r')                 
        roastFile = f.readlines()                       
        roast = str(roastFile[roastCount])              
        f.close()                                       
        
        await ctx.send(user.mention + " " + roast )           
        await logInfo(ctx,commandPrompt)                      


    # CUSTOM ROAST -- Roasts a user with a custom roast from author
    @commands.command(name='customRoast')
    async def _customRoast(self, ctx, user : discord.Member):   
        commandPrompt = "%customRoast"                                  
            
        if user.mention:
            pinged = user.mention                           
            pinged = pinged.replace("<@", "")                    
            pinged = pinged.replace(">", "")                
            pinged = pinged.replace("!", "")                
            pinged = int(pinged)                            
        else: 
            roastCount = 0
        
        msg = str(ctx.message.content)                                  
        
        if ";" in msg:                                                  
            msg = msg.split(";", 1)                                     
            roast = msg[1]                                              
        else:                                                           
            f = open(roast_path, 'r')                            
            roastFile = f.readlines()                                   
            roast = str(roastFile[0])                                   
            f.close()                                                   
            
        if pinged == 672509068174295052:                                
            f = open(roast_path, 'r')                             
            roastFile = f.readlines()                                   
            roast = str(roastFile[1])                                   
            f.close()                                                   
        elif pinged == 929071676728176733:                              
            f = open(roast_path, 'r')                             
            roastFile = f.readlines()                                   
            roast = str(roastFile[2])                                   
            f.close()                                                   
        else:
            roastLC = roast.lower()
            roastList = roastLC.split()
            badWordsList = badWords.split()
            matches = set(badWordsList).intersection(set(roastList))
            if matches:
                f = open(roast_path, 'r')                             
                roastFile = f.readlines()                                   
                roast = str(roastFile[19])                                   
                f.close()
       
        await ctx.message.delete()
        await ctx.send(roast)                                           
        await logInfo(ctx,commandPrompt)

    # MOCK -- Mocks the user's last message
    @commands.command(name='mock')
    async def _mock(self, ctx, user : discord.Member): 

        commandPrompt = "%mock"                      
        i = True                                    
        mockMessage = ""       
        
        if user.mention:
            pinged = user.mention                           
            pinged = pinged.replace("<@", "")                     
            pinged = pinged.replace(">", "")                
            pinged = pinged.replace("!", "")               
            pinged = int(pinged)                            
        else: 
            roastCount = 0                                                 
        
        async for msg in ctx.channel.history(limit = 100):                      
            if msg.author.id == pinged:                                         
                msgRef = msg
                msg = str(msg.content)                                          
                break                                                           
                
        msg = msg.replace("<@982907926199025724> ", "")                        
        
        for letter in msg:                                                     
            if i:                                                               
                mockMessage += letter.lower()                                  
            else:                                                              
                mockMessage += letter.upper()                                   
            i = not i                                                           
        embedVar = discord.Embed(description = mockMessage, color = 0x00ff00)   
        embedVar.set_thumbnail(url = mockMeme)                                  
        await ctx.send(embed=embedVar, reference=msgRef)                        
        await logInfo(ctx,commandPrompt)



    # GIF -- Sends a link to gifs of the context send
#    @commands.command(name='gif')
#    async def _gif(self, ctx): 

#        commandPrompt = "/gif"                       
#        msg = str(ctx.message.content)              
#        gifresults = "https://tenor.com/search/"    

#        msg = msg.split("/gif", 1)                  
#        gifContent = str(msg[1])                   
#        gifContent = gifContent.strip()             
        
#        gifresults += gifContent                    
        
#        await ctx.send(gifresults)                  
#        await logInfo(ctx,commandPrompt)


    # GOOGLE -- Sends the top 3 articles links for the searched topic
#    @commands.command(name='google')
#    async def _google(self, ctx): 
#        commandPrompt = "/google"                     
#        messageContent = str(ctx.message.content)                                       
#        messageContent = messageContent.replace("<@982907926199025724>", "").strip()    
#        messageContent = messageContent.replace("google", "").strip()                   
#        for url in search(messageContent, tld="co.in", num=3, stop=3, pause=2):         
#            await ctx.send(url)                                                         
#        await logInfo(ctx,commandPrompt)


bot = commands.Bot('%', description='Hi! I am Tyborg. Use the %commands command to see what all my commands do!')
bot.add_cog(Commands(bot))



@bot.event                                              
async def on_ready():                                   
    guild_count = 0                                    
    print("\n")
    
    for guild in bot.guilds:                           
        print(f"- {guild.name} (name: {guild.id})")     
        guild_count = guild_count + 1                   
    print("\nTyborg is currently running...")    

bot.run(token)                                           