import os
import asyncio
import discord
import logging
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils import checks
from __main__ import settings
from cogs.utils.chat_formatting import box, pagify

log = logging.getLogger('red.ServerWhitelist')


class ServerWhitelist:
    """
    Lets a bot owner create a list of servers that the bot will immediately
    leave any other server it joins. defaults to allowing
    It does not require you to make the bot private"""
    __author__ = "mikeshardmind"
    __version__ = "0.1"

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/serverwhitelist/settings.json')
        self.whitelist = dataIO.load_json('data/serverwhitelist/list.json')

    def save_json(self):
        dataIO.save_json("data/serverwhitelist/settings.json", self.settings)
        dataIO.save_json("data/serverwhitelist/list.json", self.whitelist)

    @checks.is_owner()
    @commands.group(name="serverwhitelist", pass_context=True)
    async def serverwhitelist(self, ctx):
        """Manage the server whitelist
        These commands will fail if not in direct message"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @checks.is_owner()
    @serverwhitelist.command(name="add", pass_context=True)
    async def whitelist_server(self, ctx, server_id=None):
        """
        whitelists a server by server ID
        because the author is lazy,
        this must be used in direct messages
        """

        if ctx.message.channel.is_private:
            if server_id is None:
                await self.bot.say("I can't whitelist a server without the ID")
            else:
                if server_id not in self.whitelist:
                    self.whitelist[server_id] = {}
                    self.save_json()
                    await self.bot.say("Server with ID: {} "
                                       "whitelisted.".format(server_id))

                else:
                    await self.bot.say("That server is already "
                                       "in the whitelist")
        else:
            try:
                await self.bot.say("You can't use that here")
            except discord.Forbidden:
                log.debug("Some Dumbass tried to use me in a "
                          "place I couldn't repsond")

    @checks.is_owner()
    @serverwhitelist.command(name="remove", pass_context=True)
    async def un_whitelist_server(self, ctx, server_id=None):
        """
        un-whitelists a server by ID
        for the sake of consistency,
        this can only be used in direct messages
        """

        if ctx.message.channel.is_private:
            if server_id is None:
                await self.bot.say("I can't remove a server from the whitelist"
                                   " without an ID")
            else:
                if server_id in list(self.whitelist):
                    del self.whitelist[server_id]
                    self.save_json()
                    await self.bot.say("Server with ID: {} no longer "
                                       "in whitelist".format(server_id))
                else:
                    await self.bot.say("There wasn't a server with that ID "
                                       "in the whitelist")
        else:
            try:
                await self.bot.say("You can't use that here")
            except discord.errors.Forbidden:
                log.debug("Some Dumbass didn't RTFM and tried to use me in a "
                          "place I couldn't resond")

    @checks.is_owner()
    @serverwhitelist.command(name="list", pass_context=True)
    async def fetch_whitelist(self, ctx):
        """
        get a list of whitelisted server's IDs
        attempts to get the corresponding name if the bot is also in a
        whitelisted server
        """

        if ctx.message.channel.is_private:
            if len(self.whitelist) > 0:
                output = "Whitelist\n"
                for k, v in self.whitelist:
                    s = self.bot.get_server(k)
                    if s is None:
                        output += "\n{}".format(k)
                    else:
                        output += "\n{0.id} : {0.name}".format(s)
                for page in pagify(output, delims=["\n", ","]):
                    await self.bot.say(box(page))
            else:
                await self.bot.say("There are no servers in the whitelist.")
        else:
            await self.bot.say("You can't use that here.")

    @checks.is_owner()
    @serverwhitelist.command(name="setmsg", pass_context=True)
    async def setleaveonwhite(self, ctx, msg=None):
        """
        sets (or clears) the message to send when leaving
        like the rest of this cog, direct message only,
        message must be enclosed in quotes
        """

        if ctx.message.channel.is_private:
            self.settings['msg'] = msg
            self.save_json
            if msg:
                await self.bot.say("Message set to: \n```{}```".format(msg))
            else:
                await self.bot.say("Leave message disabled")
        else:
            await self.bot.say("You can't use that here.")

    @checks.is_owner()
    @serverwhitelist.command(name="runnow", pass_context=True)
    async def runnow(self, ctx, msg=None):
        """
        processes all servers the bot is in
        """

        for server in self.bot.servers:
            await self.whitelist_routine(server)

    async def whitelist_routine(self, server):
        """do the thing"""

        if server.owner.id == settings.owner:
            return  # If the bot is joining your own server, you should know

        if server.id not in self.whitelist:
            channel = server.default_channel
            if channel is None:
                chan_list = [
                    c for c in sorted(
                        server.channels, key=lambda ch: ch.position
                    ) if c.type.name == "text"
                ]
                for ch in chan_list:
                    if ch.permissions_for(server.me).read_messages and \
                            ch.permissions_for(server.me).send_messages:
                        channel = ch
                        break
                else:
                    log.debug("Did not have permission to leave exit message "
                              "for any channel in server named {0.name} "
                              "with ID of {0.id} ".format(server))
                    return

            msg = self.settings.get('msg', None)

            if msg:
                try:
                    await self.bot.send_message(channel, "{}".format(msg))
                except discord.Forbidden:
                    log.debug("Did not have permission to leave exit message "
                              "for server named {0.name} with ID of {0.id} "
                              "".format(server))
                except Exception as e:
                    log.debug(e)
            await asyncio.sleep(1)
            await self.bot.leave_server(server)
            log.debug("I left a server named {} with an ID of {} "
                      "".format(server.name, server.id))


def check_folder():
    f = 'data/serverwhitelist'
    if not os.path.exists(f):
        os.makedirs(f)


def check_file():
    f = 'data/serverwhitelist/settings.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})
    f = 'data/serverwhitelist/list.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})


def setup(bot):
    check_folder()
    check_file()
    n = ServerWhitelist(bot)
    bot.add_listener(n.whitelist_routine, "on_server_join")
    bot.add_cog(n)
