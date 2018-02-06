#!/usr/bin/env python2.7

# =============================================================================
# IMPORTS
# =============================================================================
import traceback
import praw
import re
import MySQLdb
import configparser
import ast
import time
import urllib
import requests
from datetime import datetime
from praw.exceptions import APIException, PRAWException
from threading import Thread

# =============================================================================
# GLOBALS
# =============================================================================

# Reads the config file
config = configparser.ConfigParser()
config.read("remindmebot.cfg")

bot_username = config.get("Reddit", "username")
bot_password = config.get("Reddit", "password")
client_id = config.get("Reddit", "client_id")
client_secret = config.get("Reddit", "client_secret")

#Reddit info
reddit = praw.Reddit(client_id=client_id,
                     client_secret=client_secret,
                     password=bot_password,
                     user_agent='cryptoRemindMe by /u/boyAndHisBlob',
                     username=bot_username)

DB_USER = config.get("SQL", "user")
DB_PASS = config.get("SQL", "passwd")

#Dictionary to store current crypto prices
current_price = {"XRP": 0.0}

supported_tickers = ["ADA","BCH","BCN","BTC","BTG","DASH","ETC","ETH","LSK","LTC","MIOTA","NEO","QTUM","STEEM","XEM","XLM","XMR","XRB","XRP","ZEC"]

# =============================================================================
# CLASSES
# =============================================================================

class DbConnection(object):
    """
    DB connection class
    """
    connection = None
    cursor = None

    def __init__(self):
        self.connection = MySQLdb.connect(
            host="localhost", user=DB_USER, passwd=DB_PASS, db="crypto_remind_me"
        )
        self.cursor = self.connection.cursor()

class Search(object):
    commented = [] # comments already replied to
    subId = [] # reddit threads already replied in
    
    # Fills subId with previous threads. Helpful for restarts
    database = DbConnection()
    cmd = "SELECT list FROM comment_list WHERE id = 1"
    database.cursor.execute(cmd)
    data = database.cursor.fetchall()
    subId = ast.literal_eval("[" + data[0][0] + "]")
    database.connection.commit()
    database.connection.close()

    endMessage = (
        "\n\n_____\n\n"
        "|[^(FAQs)](http://np.reddit.com/r/RemindMeBot/comments/24duzp/remindmebot_info/)"
        "|[^(Custom)](http://np.reddit.com/message/compose/?to=cryptoRemindMeBot&subject=Reminder&message="
            "[LINK INSIDE SQUARE BRACKETS else default to FAQs]%0A%0A"
            "NOTE: Don't forget to add the ticker and price after the command.%0A%0AcryptoRemindMe!)"
        "|[^(Your Reminders)](http://np.reddit.com/message/compose/?to=cryptoRemindMeBot&subject=List Of Reminders&message=MyReminders!)"
        "|[^(Feedback)](http://np.reddit.com/message/compose/?to=boyAndHisBlob&subject=Feedback)"
        "|[^(Code)](https://github.com/jjmerri/cryptoRemindMe-Reddit)"
        "\n|-|-|-|-|-|-|"
        )

    def __init__(self, comment):
        self._db_connection = DbConnection()
        self.comment = comment # Reddit comment Object
        self._message_input = '"Hello, I\'m here to remind you to see the parent comment!"'
        self._store_price = None
        self._ticker = None
        self._reply_message = ""
        self._replyDate = None
        self._privateMessage = False
        self._originDate = datetime.fromtimestamp(comment.created_utc)
        
    def run(self, privateMessage=False):
        self._privateMessage = privateMessage
        self._parse_comment()
        self._save_to_db()
        self._build_message()
        self._reply()
        if self._privateMessage == True:
            # Makes sure to marks as read, even if the above doesn't work
            self.comment.mark_as_read()
            self._find_bot_child_comment()
        self._db_connection.connection.close()

    def _parse_comment(self):
        """
        Parse comment looking for the message and price
        """
        command_regex = r'!?cryptoRemindMe!?[ ]+(?P<ticker>[^ ]+)[ ]+\$?(?P<price>[\d,]+(\.\d+)?)([ ]+)?(?P<message>"[^"]+")?'

        if self._privateMessage == True:
            permalink_temp = re.search('\[(.*?)\]', self.comment.body)
            if permalink_temp:
                self.comment.permalink = permalink_temp.group()[1:-1]
                # Makes sure the URL is real
                try:
                    urllib.urlopen(self.comment.permalink)
                except IOError:
                    self.comment.permalink = "http://np.reddit.com/r/RemindMeBot/comments/24duzp/remindmebot_info/"
            else:
                # Defaults when the user doesn't provide a link
                self.comment.permalink = "http://np.reddit.com/r/RemindMeBot/comments/24duzp/remindmebot_info/"

        # remove cryptoRemindMe! or !cryptoRemindMe (case insenstive)
        match = re.search(command_regex, self.comment.body, re.IGNORECASE)

        if match:
            self._ticker = match.group("ticker").upper()
            self._store_price = match.group("price").replace(",","")
            self._message_input = match.group("message")
        else:
            #Respond with correct format
            pass
    def _save_to_db(self):
        """
        Saves the id of the comment, the current price, and the message to the DB
        """

        cmd = "INSERT INTO reminder (object_name, message, new_price, origin_price, userID, permalink, ticker, comment_create_datetime) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        self._db_connection.cursor.execute(cmd, (
                        self.comment.id.encode('utf-8'),
                        self._message_input.encode('utf-8') if self._message_input else None,
                        self._store_price,
                        current_price[self._ticker],
                        self.comment.author,
                        self.comment.permalink.encode('utf-8'),
                        self._ticker.encode('utf-8'),
                        self._originDate))
        self._db_connection.connection.commit()
        # Info is added to DB, user won't be bothered a second time
        self.commented.append(self.comment.id)

    def _build_message(self, is_for_comment = True):
        """
        Buildng message for user
        """
        permalink = self.comment.permalink
        self._reply_message =(
            "I will be messaging you when the price of {ticker} reaches **${price}** from its current price **${current_price}**"
            " to remind you of [**this link.**]({commentPermalink})"
            "{remindMeMessage}")

        try:
            self.sub = reddit.comment(self.comment.id)
        except Exception as err:
            print(err)
        if self._privateMessage is False and is_for_comment and self.sub.id not in self.subId:
            remindMeMessage = (
                "\n\n[**CLICK THIS LINK**](http://np.reddit.com/message/compose/?to=cryptoRemindMeBot&subject=Reminder&message="
                "[{permalink}]%0A%0AcryptoRemindMe! {ticker} ${price}) to send a PM to also be reminded and to reduce spam."
                "\n\n^(Parent commenter can ) [^(delete this message to hide from others.)]"
                "(http://np.reddit.com/message/compose/?to=cryptoRemindMeBot&subject=Delete Comment&message=Delete! ____id____)").format(
                    permalink=permalink,
                    price=self._store_price.replace('\n', ''),
                    ticker = self._ticker
                )
        else:
            remindMeMessage = ""

        self._reply_message = self._reply_message.format(
                remindMeMessage = remindMeMessage,
                commentPermalink = permalink,
                price = self._store_price,
                ticker = self._ticker,
                current_price = current_price[self._ticker])
        self._reply_message += Search.endMessage

    def _reply(self):
        """
        Messages the user letting as a confirmation
        """

        author = self.comment.author
        def send_message():
            self._build_message(False)
            reddit.redditor(str(author)).message('cryptoRemindMeBot Confirmation Sent', self._reply_message)

        try:
            if self._privateMessage == False:
                # First message will be a reply in a thread
                # afterwards are PM in the same thread
                if (self.sub.id not in self.subId):
                    self.subId.append(self.sub.id)
                    # adding it to database as well
                    database = DbConnection()
                    insertsubid = ", \'" + self.sub.id + "\'"
                    cmd = 'UPDATE comment_list set list = CONCAT(list, "{0}") where id = 1'.format(insertsubid)
                    database.cursor.execute(cmd)
                    database.connection.commit()
                    database.connection.close()

                    newcomment = self.comment.reply(self._reply_message)
                    # grabbing comment just made
                    reddit.comment((newcomment.id)
                        ).edit(self._reply_message.replace('____id____', str(newcomment.id)))
                else:
                    send_message()
            else:
                print(str(author))
                send_message()
        except APIException as err: # Catch any less specific API errors
            print(err)
            if err.error_type == "RATELIMIT":
                send_message()

        except PRAWException as err:
            print(err)
            # PM when I message too much
            send_message()
            time.sleep(10)

    def _find_bot_child_comment(self):
        """
        Finds the cryptoRemindMeBot comment in the child
        """
        try:
            # Grabbing all child comments
            replies = reddit.get_submission(url=self.comment.permalink).comments[0].replies
            # Look for bot's reply
            commentfound = ""
            if replies:
                for comment in replies:
                    if str(comment.author) == "cryptoRemindMeBot":
                        commentfound = comment
                self.comment_count(commentfound)
        except Exception as err:
            pass
            
    def comment_count(self, commentfound):
        """
        Posts edits the count if found
        """
        query = "SELECT count(DISTINCT userid) FROM reminder WHERE object_name = %s"
        self._db_connection.cursor.execute(query, [self.comment.id])
        data = self._db_connection.cursor.fetchall()
        # Grabs the tuple within the tuple, a number/the dbcount
        dbcount = count = str(data[0][0])
        comment = reddit.get_info(thing_id='t1_'+str(commentfound.id))
        body = comment.body

        pattern = r'(\d+ OTHERS |)CLICK(ED|) THIS LINK'
        # Compares to see if current number is bigger
        # Useful for after some of the reminders are sent, 
        # a smaller number doesnt overwrite bigger
        try:
            currentcount = int(re.search(r'\d+', re.search(pattern, body).group(0)).group())
        # for when there is no number
        except AttributeError as err:
            currentcount = 0
        if currentcount > int(dbcount):
            count = str(currentcount + 1)
        # Adds the count to the post
        body = re.sub(
            pattern, 
            count + " OTHERS CLICKED THIS LINK", 
            body)
        comment.edit(body)
def grab_list_of_reminders(username):
    """
    Grabs all the reminders of the user
    """
    database = DbConnection()
    query = "SELECT object_name, message, new_date, id FROM reminder WHERE userid = %s ORDER BY new_date"
    database.cursor.execute(query, [username])
    data = database.cursor.fetchall()
    table = (
            "[**Click here to delete all your reminders at once quickly.**]"
            "(http://np.reddit.com/message/compose/?to=cryptoRemindMeBot&subject=Reminder&message=RemoveAll!)\n\n"
            "|Permalink|Message|Date|Remove|\n"
            "|-|-|-|:-:|")
    for row in data:
        date = str(row[2])
        table += (
            "\n|" + row[0] + "|" +   row[1] + "|" + 
            "[" + date  + " UTC](http://www.wolframalpha.com/input/?i=" + str(row[2]) + " UTC to local time)|"
            "[[X]](https://np.reddit.com/message/compose/?to=cryptoRemindMeBot&subject=Remove&message=Remove!%20"+ str(row[3]) + ")|"
            )
    if len(data) == 0: 
        table = "Looks like you have no reminders. Click the **[Custom]** button below to make one!"
    elif len(table) > 9000:
        table = "Sorry the comment was too long to display. Message /u/RemindMeBotWrangler as this was his lazy error catching."
    table += Search.endMessage
    return table

def remove_reminder(username, idnum):
    """
    Deletes the reminder from the database
    """
    database = DbConnection()
    # only want userid to confirm if owner
    query = "SELECT userid FROM reminder WHERE id = %s"
    database.cursor.execute(query, [idnum])
    data = database.cursor.fetchall()
    deleteFlag = False
    for row in data:
        userid = str(row[0])
        # If the wrong ID number is given, item isn't deleted
        if userid == username:
            cmd = "DELETE FROM reminder WHERE id = %s"
            database.cursor.execute(cmd, [idnum])
            deleteFlag = True

    
    database.connection.commit()
    return deleteFlag

def remove_all(username):
    """
    Deletes all reminders at once
    """
    database = DbConnection()
    query = "SELECT * FROM reminder where userid = %s"
    database.cursor.execute(query, [username])
    count = len(database.cursor.fetchall())
    cmd = "DELETE FROM reminder WHERE userid = %s"
    database.cursor.execute(cmd, [username])
    database.connection.commit()

    return count

def read_pm():
    try:
        for message in reddit.inbox.unread(limit = 100):
            # checks to see as some comments might be replys and non PMs
            prawobject = isinstance(message, praw.models.Message)
            if (("cryptoremindme" in message.body.lower() or
                "cryptoremindme!" in message.body.lower() or
                "!cryptoremindme" in message.body.lower()) and prawobject):
                redditPM = Search(message)
                redditPM.run(privateMessage=True)
                message.mark_as_read()
            elif (("delete!" in message.body.lower() or "!delete" in message.body.lower()) and prawobject):  
                givenid = re.findall(r'delete!\s(.*?)$', message.body.lower())[0]
                givenid = 't1_'+givenid
                comment = reddit.get_info(thing_id=givenid)
                try:
                    parentcomment = reddit.get_info(thing_id=comment.parent_id)
                    if message.author.name == parentcomment.author.name:
                        comment.delete()
                except ValueError as err:
                    # comment wasn't inside the list
                    pass
                except AttributeError as err:
                    # comment might be deleted already
                    pass
                message.mark_as_read()
            elif (("myreminders!" in message.body.lower() or "!myreminders" in message.body.lower()) and prawobject):
                listOfReminders = grab_list_of_reminders(message.author.name)
                message._reply(listOfReminders)
                message.mark_as_read()
            elif (("remove!" in message.body.lower() or "!remove" in message.body.lower()) and prawobject):
                givenid = re.findall(r'remove!\s(.*?)$', message.body.lower())[0]
                deletedFlag = remove_reminder(message.author.name, givenid)
                listOfReminders = grab_list_of_reminders(message.author.name)
                # This means the user did own that reminder
                if deletedFlag == True:
                    message._reply("Reminder deleted. Your current Reminders:\n\n" + listOfReminders)
                else:
                    message._reply("Try again with the current IDs that belong to you below. Your current Reminders:\n\n" + listOfReminders)
                message.mark_as_read()
            elif (("removeall!" in message.body.lower() or "!removeall" in message.body.lower()) and prawobject):
                count = str(remove_all(message.author.name))
                listOfReminders = grab_list_of_reminders(message.author.name)
                message._reply("I have deleted all **" + count + "** reminders for you.\n\n" + listOfReminders)
                message.mark_as_read()
    except Exception as err:
        print(traceback.format_exc())

def check_comment(comment):
    """
    Checks the body of the comment, looking for the command
    """
    reddit_call = Search(comment)
    if (("cryptoremindme!" in comment.body.lower() or
        "!cryptoremindme" in comment.body.lower()) and
        reddit_call.comment.id not in reddit_call.commented and
        'cryptoRemindMeBot' != str(comment.author) and
        'cryptoRemindMeBotTst' != str(comment.author)):
            print("Running Thread")
            t = Thread(target=reddit_call.run())
            t.start()

def check_own_comments():
    user = reddit.redditor("cryptoRemindMeBot")
    for comment in user.get_comments(limit=None):
        if comment.score <= -5:
            print("COMMENT DELETED")
            print(comment)
            comment.delete()

def update_crypto_prices():
    """
    updates supported crypto prices with current exchange price
    """

    r = requests.get("https://min-api.cryptocompare.com/data/pricemulti?fsyms={supported_ticket_list}&tsyms=USD&e=CCCAGG"
                    .format(
                        supported_ticket_list = ','.join(map(str, supported_tickers))
                    ))
    response = r.json()

    for price in response:
        current_price[price] = response[price]["USD"]

#returns the time saved in lastrunsearch.txt
#returns 10000 if 0 is in the file because it will break the http call with 0
def get_last_run_time():
    lastrun_file = open("lastrunsearch.txt", "r")
    last_run_time = int(lastrun_file.read())
    lastrun_file.close()

    if last_run_time:
        return last_run_time
    else:
        return 10000

# =============================================================================
# MAIN
# =============================================================================

def main():
    print("start")
    checkcycle = 0
    last_processed_time = get_last_run_time()
    while True:
        try:
            update_crypto_prices()
            # grab the request
            request = requests.get('https://api.pushshift.io/reddit/search/comment/?q=%22cryptoRemindMe%22&limit=100&after=' + str(last_processed_time),
                headers = {'User-Agent': 'cryptoRemindMeBot-Agent'})
            json = request.json()
            comments =  json["data"]
            read_pm()
            for rawcomment in comments:
                if last_processed_time < rawcomment["created_utc"]:
                    last_processed_time = rawcomment["created_utc"]

                # object constructor requires empty attribute
                rawcomment['_replies'] = ''
                comment = praw.models.Comment(reddit, id = rawcomment["id"])
                check_comment(comment)

            # Only check periodically 
            if checkcycle >= 5:
                check_own_comments()
                checkcycle = 0
            else:
                checkcycle += 1

            lastrun_file = open("lastrunsearch.txt", "w")
            lastrun_file.write(str(last_processed_time))
            lastrun_file.close()

            print("----")
            time.sleep(30)
        except Exception as err:
            print(traceback.format_exc())
            time.sleep(30)
# =============================================================================
# RUNNER
# =============================================================================

if __name__ == '__main__':
    main()
