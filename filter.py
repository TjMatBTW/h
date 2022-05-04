import discord, re, json, aiosqlite, asyncio
from discord.ext import commands,tasks
import humanfriendly
from humanfriendly import format_timespan
import datetime

class FilterCog(commands.Cog, name = "Filter"):
    """Commands for filtering things"""

    def __init__(self, bot):
        self.bot = bot
        
    async def filter_message(self,message):
        async with aiosqlite.connect('filter.db') as connection:
            async with connection.cursor() as cursor:
                await cursor.execute('SELECT words, ignored, enabled, mod, duration FROM guilds WHERE id = ?',(message.guild.id,))
                data = await cursor.fetchone()
                if data:
                    enabled = data[2]
                    words = None
                    duration = data[4]
                    mod = data[3]
                    try:
                        words = json.loads(data[0])
                        ignored = json.loads(data[1])
                    except:
                        words = words or []
                        ignored = []
                else:
                    return
        for_roles = False
        for role in message.author.roles:
            if role.id in ignored:
                for_roles = True
                break
        ignore_it = message.channel.id in ignored or message.author.id in ignored or message.channel.category_id in ignored or for_roles
        if enabled and not ignore_it and not message.author.bot:
            for word in words:
                pattern = r'(?i)(\b' + r'+\W*'.join(word) + f'|{word})' if word.isalnum() else word
                if re.search(pattern,message.content):
                    try:
                        await message.delete()
                    except:
                        pass
                    if mod == True:
                        await message.channel.send(embed=discord.Embed(title="User Muted", description=f"**{message.author.name} has been muted for using a filtered word!**", color=discord.Color.red()))
                        await message.author.send(embed=discord.Embed(description=f"**<a:no:932136870148702209> You have been muted for using a filtered word in {message.guild.name}!**", color=discord.Color.red()))
                        try:
                            await message.author.timeout_for(duration=duration, reason="Using a Filtered Word")
                        except:
                            pass
                    else:
                        pass
        else:
            return


    # LISTENERS #

    @commands.Cog.listener()
    async def on_ready(self):
        async with aiosqlite.connect('filter.db') as connection:
            async with connection.cursor() as cursor:
                await cursor.execute('CREATE TABLE IF NOT EXISTS guilds (id INTEGER, ignored TEXT, words TEXT, enabled BOOL, mod BOOL,duration TEXT);')
                await connection.commit()

    @commands.Cog.listener()
    async def on_message(self,message):
        try:
            await self.filter_message(message)
        except:
            return

    @commands.Cog.listener()
    async def on_message_edit(self,before,after):
        try:
            await self.filter_message(after)
        except:
            return
            
    # COMMANDS #

    @commands.group(invoke_without_command=True)
    @commands.has_permissions(manage_channels=True)
    async def filter(self,ctx):
        """Toggle the word filter. When the filter is on, messages are automatically deleted."""
        async with aiosqlite.connect('filter.db') as connection:
            async with connection.cursor() as cursor:
                await cursor.execute('SELECT enabled FROM guilds WHERE id = ?',(ctx.guild.id,))
                previous = await cursor.fetchone()
                if not previous:
                    await cursor.execute('INSERT INTO guilds (id, ignored, words, enabled, mod) VALUES (?,?,?,?,?)',(ctx.guild.id,'','',True,False,))
                    previous = False
                else:
                    previous = previous[0]
                    await cursor.execute('UPDATE guilds SET enabled = ? WHERE id = ?',(not previous,ctx.guild.id,))
                await connection.commit()
        
        embed = discord.Embed(description=f"<a:yes:932097539010854932> | Filter Status: {not previous}",color=discord.Color.green())     
        await ctx.send(embed=embed)

    @filter.command()
    @commands.has_permissions(manage_channels=True)
    async def add(self,ctx,word):
        """Add a word to the filter"""
        try:
            await ctx.message.delete()
        except:
            pass
        async with aiosqlite.connect('filter.db') as connection:
            async with connection.cursor() as cursor:
                await cursor.execute('SELECT words FROM guilds WHERE id = ?',(ctx.guild.id,))
                data = await cursor.fetchone()
                if data:
                    try:
                        words = json.loads(data[0])
                    except:
                        words = []
                    if not word in words:
                        words.append(word)
                        await cursor.execute('UPDATE guilds SET words = ? WHERE id = ?',(json.dumps(words),ctx.guild.id,))
                        embed = discord.Embed(description=f"**<a:yes:932097539010854932> {word} has been added to the filter!**",color=discord.Color.green())
                        await ctx.send(embed=embed)
                    else:
                        embed=discord.Embed(description="**<a:no:932136870148702209> That word is already in the filter**", color=discord.Color.red())
                        await ctx.send(embed=embed)
                else:
                    await cursor.execute('INSERT INTO guilds (id, ignored, words, enabled) VALUES (?,?,?,?)',(ctx.guild.id,'',json.dumps([word]),False,))
                await connection.commit()

    @filter.command()
    @commands.has_permissions(manage_channels=True)
    async def remove(self,ctx,word):
        """Remove a word from the filter"""
        try:
            await ctx.message.delete()
        except:
            pass
        async with aiosqlite.connect('filter.db') as connection:
            async with connection.cursor() as cursor:
                await cursor.execute('SELECT words FROM guilds WHERE id = ?',(ctx.guild.id,))
                data = await cursor.fetchone()
                if data:
                    if data[0]:
                        words = json.loads(data[0])
                    else:
                        words = []
                    if word in words:
                        words.remove(word)
                        await cursor.execute('UPDATE guilds SET words = ? WHERE id = ?',(json.dumps(words),ctx.guild.id,))
                        embed = discord.Embed(description=f"**<a:yes:932097539010854932> {word} has been removed from the filter!**",color=discord.Color.green())
                        await ctx.send(embed=embed)
                    else:
                        embed=discord.Embed(description="**<a:no:932136870148702209> That word is not in the server filter!**", color=discord.Color.red())
                        await ctx.send(embed=embed)
                else:
                    await cursor.execute('INSERT INTO guilds (id, ignored, words, enabled) VALUES (?,?,?,?)',(ctx.guild.id,'',json.dumps([word]),False,))
                await connection.commit()
    
    @filter.command(aliases=['list'])
    @commands.has_permissions(manage_channels=True)
    async def words(self,ctx):
        """Get a list of currently filtered words"""
        async with aiosqlite.connect('filter.db') as connection:
            async with connection.cursor() as cursor:
                await cursor.execute('SELECT words FROM guilds WHERE id = ?',(ctx.guild.id,))
                data = await cursor.fetchone()
        try:
            try:
                data = json.loads(data[0])
            except:
                embed=discord.Embed(description="**<a:no:932136870148702209> No Word Filter Configured in this Server**", color=discord.Color.red())
                return await ctx.send(embed=embed)
            if len(data) > 0:
                embed = discord.Embed(title=f"{ctx.guild.name}'s Filter List",description=f"`{', '.join(data)}`",color=discord.Color.green())
                await ctx.author.send(embed=embed)
            else:
                embed=discord.Embed(description="**<a:no:932136870148702209> No words found in the Filter!**", color=discord.Color.red())
                await ctx.author.send(embed=embed)
            embed = discord.Embed(description=f"<a:yes:932097539010854932> Please check your DMs for the Filter List!",color=discord.Color.green())    
            await ctx.send(embed=embed)
        except:
            embed=discord.Embed(description="**<a:no:932136870148702209> Please enable your DMs for this Server!**", color=discord.Color.red())
            await ctx.send(embed=embed)

    @filter.command()
    @commands.has_permissions(manage_channels=True)
    async def ignore(self,ctx,object):
        """Ignore a channel, channel category, member, or role. If it is already ignored the bot will stop ignoring it."""
        channel = object
        try:
            channel = await discord.ext.commands.MemberConverter().convert(ctx,channel)
        except discord.ext.commands.errors.MemberNotFound:
            try:
                channel = await discord.ext.commands.TextChannelConverter().convert(ctx,channel)
            except discord.ext.commands.errors.ChannelNotFound:
                try:
                    channel = await discord.ext.commands.CategoryChannelConverter().convert(ctx,channel)
                except discord.ext.commands.errors.ChannelNotFound:
                    try:
                        channel = await discord.ext.commands.RoleConverter().convert(ctx,channel)
                    except discord.ext.commands.errors.RoleNotFound:
                        return await ctx.send(f'**<a:no:932136870148702209> I couldnt find `{object}`**')
        
        async with aiosqlite.connect('filter.db') as connection:
            async with connection.cursor() as cursor:
                await cursor.execute('SELECT ignored FROM guilds WHERE id = ?',(ctx.guild.id,))
                data = await cursor.fetchone()
                if data:
                    if data[0]:
                        channels = json.loads(data[0])
                    else:
                        channels = []
                    embed = discord.Embed(title='Filter Ignore SYS')
                    if not channel.id in channels:
                        channels.append(channel.id)
                        embed.description=f"<a:yes:932097539010854932> Ok, I will start ignoring {channel.mention}"
                        await ctx.send(embed=embed)
                    else:
                        channels.remove(channel.id)
                        embed.description=f"<a:yes:932097539010854932> Ok, I will stop ignoring {channel.mention}"
                        await ctx.send(embed=embed)
                    await cursor.execute('UPDATE guilds SET ignored = ? WHERE id = ?',(json.dumps(channels),ctx.guild.id,))
                    await connection.commit()
                else:
                    embed=discord.Embed(description="**<a:no:932136870148702209> Please enable the filter first!**", color=discord.Color.red())
                    await ctx.send(embed=embed)
                                      
    @filter.command()
    @commands.has_guild_permissions(manage_channels=True)
    async def ignored(self, ctx):
        """List the ignored places in your server"""
        async with aiosqlite.connect('filter.db') as connection:
            async with connection.cursor() as cursor:
                await cursor.execute('SELECT ignored FROM guilds WHERE id = ?',(ctx.guild.id,))
                data = await cursor.fetchone()
                if data:
                    try:
                        ignored = json.loads(data[0])
                    except:
                        ignored = ['None']
                else:
                    return
                all_ids = ctx.guild.text_channels + ctx.guild.members + ctx.guild.roles + ctx.guild.categories
                embed = discord.Embed(title="Ignored",description=' '.join([discord.utils.get(all_ids,id=id).mention for id in ignored]) if ignored != 'None' else ignored)
                await ctx.send(embed=embed)

    @commands.group(name="automod",invoke_without_command=True)
    @commands.has_permissions(manage_channels=True)
    async def automod(self, ctx):
        """Turn on/off AutoMod in your server."""
        async with aiosqlite.connect('filter.db') as connection:
            async with connection.cursor() as cursor:
                await cursor.execute('SELECT mod FROM guilds WHERE id = ?',(ctx.guild.id,))
                previous = await cursor.fetchone()
                if not previous:
                    await cursor.execute('INSERT INTO guilds (id, mod) VALUES (?,?)',(ctx.guild.id, True))
                    previous = False
                else:
                    previous = previous[0]
                    await cursor.execute('UPDATE guilds SET mod = ? WHERE id = ?',(not previous,ctx.guild.id,))
                await connection.commit()
        
        embed = discord.Embed(description=f"**<a:yes:932097539010854932> | AutoMod Status: {not previous}\nTip: Set a duration with the command `+automod duration`!**",color=discord.Color.green())     
        await ctx.send(embed=embed)

    @automod.command()
    @commands.has_permissions(manage_channels=True)
    async def duration(self, ctx,*,time=None):
        """Sets the duration of a filtered message."""
        if time == None:
            await ctx.send(embed=discord.Embed(description="**<a:no:932136870148702209> No Time was specified! Duration has been defaulted to 30 minutes!**", color=discord.Color.red()))
            time = "30 minutes"       
        timed = humanfriendly.parse_timespan(time) 
        num = int(timed) 
        if num < 60:
            return await ctx.send(embed=discord.Embed(description="**<a:no:932136870148702209> You can't set the duration for under a minute!**", color=discord.Color.red()))
        if num > 604800:
            return await ctx.send(embed=discord.Embed(description="**<a:no:932136870148702209> You can't set the duration for more than a week!**", color=discord.Color.red()))
        duration = datetime.timedelta(seconds=num)
        async with aiosqlite.connect('filter.db') as connection:
            async with connection.cursor() as cursor:
                await cursor.execute('UPDATE guilds SET duration = ? WHERE id = ?',(str(duration),ctx.guild.id,))
                await connection.commit()
        embed = discord.Embed(description=f"**<a:yes:932097539010854932> Duration has been setted to `{time}`**", color=discord.Color.green())
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(FilterCog(bot))
