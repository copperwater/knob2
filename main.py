"""
   Main module, demonstrates setting up and using a bot.
"""

import bot
import irc_message
import pymongo
from bson.objectid import ObjectId
import sys
import re
import time

mclient = pymongo.MongoClient('localhost', 27017)
db = mclient['jbot']

# Given a nick, return a dictionary representing the associated user in the database.
# This will create a user if no user with the nick exists.
def get_user(nick):
   user = db.users.find_one({'nick': nick})
   if user is None:
      new_user = {
         'nick': nick,
         'karma': 0,
      }
      new_id = db.users.insert(new_user)
      user = db.users.find_one({'_id': ObjectId(new_id)})
   return user


# Given a list of nicks with ++ or -- after them, adjust each user's karma accordingly.
def adjust_karma(karma_mod_list, bot, channel):
   for s in karma_mod_list:
      has_plusplus = ( s.find('++') >= 0 )
      has_minusminus = ( s.find('--') >= 0 )

      if has_plusplus and has_minusminus:
         # string has both ++ and -- in it, someone is probably trying to confuse the bot
         if len(karma_mod_list) == 1:
            bot.say("Don't try to break me.", channel)
            return
         # if there are other karma mods, go to them
         continue

      elif has_plusplus:
         delta = 1
      elif has_minusminus:
         delta = -1
      else:
         # neither ++ or -- happened, this should not be possible
         print 'Warning: karma_mod_list encountered a name not followed by ++ or --:', s
         continue

      nick = s.rstrip('+-')
      user = get_user(nick)
      print user
      new_karma = user['karma'] + delta
      db.users.update({'nick': nick}, { '$set':  { 'karma': new_karma } })
      point_str = "point" if (new_karma == 1 or new_karma == -1) else "points"
      bot.say(nick + ' now has ' + str(new_karma) + ' ' + point_str + ' of karma', channel)


# Save a message from someone in the database so it can be retrieved later.
def save_quote(message, sender):
   quotes_singleton = db.singletons.find_one({'collection': 'quotes'})
   numquotes = quotes_singleton['total_quotes']
   newquote = {
      'author': sender,
      'quote': message,
      'tstamp': time.time(),
      'index': numquotes,
   }

   # see if this quote contains "is" or "are" so it can be marked specially
   isare = re.findall('([^\s]+)\s+(?:is|are)', message)
   if len(isare) > 0:
      newquote['is'] = isare

   db.quotes.insert(newquote)
   db.singletons.update({'collection': 'quotes'}, {'total_quotes': numquotes+1})
   # user = get_user(sender)
   # db.users.update({'nick': sender}, {'$push': {'quotes': message}})


# Handle a command to the bot. Commands could be virtually anything.
def handle_command(bot, message, sender):
   cmd_list = message.split()
   # cmd_list[0] is expected to be the bot's name
   if len(cmd_list) < 2:
      # can't really do anything without a command
      return

   if cmd_list[1] == 'quote':
      # pick random number mod numquotes and get the quote with that index


# Hook for PRIVMSG commands and reacting to them. This will be the biggest part of most bots.
def privmsg_fn(bot, msg):
   sender = msg.getName()
   recipient = msg.params[0]
   message = msg.trail

   # look for a command to the bot (denoted by any string starting with the bot's nick)
   if message.find(bot.nick) == 0:
      handle_command(bot, message, sender)

   is_private = (recipient == bot.nick)

   if not is_private:
      # public message in a channel
      channel = recipient

      # look for a ++ or -- in the string (karma up/down)
      karma_mod_list = re.findall('[^ ]+(?:\+\+|--)', message)
      if len(karma_mod_list) > 0:
         # do not record karma mods as quotes
         adjust_karma(karma_mod_list, bot, channel)
         return

      # add this message to the database of quotes for this sender
      save_quote(message, sender)

   # bot.say(msg.trail, recipient)

settings = {
}


jbot = bot.Bot(settings)
jbot.add_hook('PRIVMSG', privmsg_fn)
# jbot.connect('irc.freenode.net', 'sjdhfkj')
jbot.connect('irc.devel.redhat.com', 'jbeck_bot')
jbot.join('#cee-tools-interns')
jbot.interact()
