#!/usr/bin/env python2.7

# =============================================================================
# IMPORTS
# =============================================================================

import praw
import MySQLdb
import configparser
import time
import requests
from datetime import datetime
from requests.exceptions import HTTPError, ConnectionError, Timeout
from praw.exceptions import APIException, ClientException, PRAWException
from socket import timeout
from pytz import timezone

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
                     user_agent='xrpRemindMe by /u/boyAndHisBlob',
                     username=bot_username)
# DB Info
DB_USER = config.get("SQL", "user")
DB_PASS = config.get("SQL", "passwd")

# =============================================================================
# CLASSES
# =============================================================================

class Connect(object):
    """
    DB connection class
    """
    connection = None
    cursor = None

    def __init__(self):
        self.connection = MySQLdb.connect(
            host="localhost", user=DB_USER, passwd=DB_PASS, db="xrp_remind_me"
        )
        self.cursor = self.connection.cursor()

class Reply(object):

    def __init__(self):
        self._queryDB = Connect()
        self._replyMessage =(
            "xrpRemindMe private message here!" 
            "\n\n**The message:** \n\n>{message}"
            "\n\n**The original comment:** \n\n>{original}"
            "\n\n**The parent comment from the original comment or its submission:** \n\n>{parent}"
            "{origin_date_text}"
            "\n\nYou requested a reminder when the price reached {new_price} from {origin_price}."
            "\n\nThe price hit {price} at {price_time} on bitfinex"
            "\n\n_____\n\n"
            "|[^(FAQs)](http://np.reddit.com/r/RemindMeBot/comments/24duzp/remindmebot_info/)"
            "|[^(Your Reminders)](http://np.reddit.com/message/compose/?to=xrpRemindMeBot&subject=List Of Reminders&message=MyReminders!)"
            "|[^(Feedback)](http://np.reddit.com/message/compose/?to=boyAndHisBlob&subject=xrpRemindMe Feedback)"
            "|[^(Code)](https://github.com/jjmerri/xrpRemindMe-Reddit)"
            "\n|-|-|-|-|-|-|"
            )
        self._high = 0.00
        self._low = 10000.00
        self._last_price_time = 0


    def set_interval_extremes(self):
        """
        Replies a second time to the user after a set amount of time
        """

        lastrun_file = open("lastrun.txt", "r")
        current_time_sec = int(time.time())
        mins_since_lastrun = (current_time_sec - int(lastrun_file.read())) // 60

        lastrun_file.close()

        r = requests.get('https://min-api.cryptocompare.com/data/histominute?fsym=XRP&tsym=USD&e=bitfinex&limit=' + str(mins_since_lastrun))
        response = r.json()
        minutes_data = response['Data']

        for minute_data in minutes_data:
            high = minute_data['high']
            low = minute_data['low']

            if high > self._high:
                self._high = high
                self._high_time = minute_data['time']

            if low < self._low:
                self._low = low
                self._low_time = minute_data['time']

            if minute_data['time'] > self._last_price_time:
                self._last_price_time = minute_data['time']


    def parent_comment(self, commentId):
        """
        Returns the parent comment or if it's a top comment
        return the original submission
        """
        try:
            commentObj = reddit.comment(id=_force_utf8(commentId))
            if commentObj.is_root:
                return _force_utf8(commentObj.submission.permalink)
            else:
                return _force_utf8(commentObj.parent().permalink)
        except IndexError as err:
            print("parrent_comment error")
            return "It seems your original comment was deleted, unable to return parent comment."
        # Catch any URLs that are not reddit comments
        except Exception  as err:
            print(err)
            print("HTTPError/PRAW parent comment")
            return "Parent comment not required for this URL."

    def time_to_reply(self):
        """
        Checks to see through SQL if net_date is < current time
        """

        # get current time to compare
        currentTime = datetime.now(timezone('UTC'))
        currentTime = format(currentTime, '%Y-%m-%d %H:%M:%S')
        cmd = "SELECT * FROM message_date WHERE (new_price <= %s AND new_price >= origin_price) OR (new_price >= %s AND new_price <= origin_price)"
        self._queryDB.cursor.execute(cmd, [self._high, self._low])

    def search_db(self):
        """
        Loop through data looking for which comments are old
        """

        data = self._queryDB.cursor.fetchall()
        alreadyCommented = []
        for row in data:
            # checks to make sure ID hasn't been commented already
            # For situtations where errors happened
            if row[0] not in alreadyCommented:
                flagDelete = False
                # MySQl- object_name, message, create date, reddit user, new_price, origin_price
                flagDelete = self.new_reply(row[1],row[2], row[6], row[5], row[3], row[4], row[8])
                # removes row based on flagDelete
                if flagDelete:
                    cmd = "DELETE FROM message_date WHERE id = %s" 
                    self._queryDB.cursor.execute(cmd, [row[0]])
                    self._queryDB.connection.commit()
                    alreadyCommented.append(row[0])

        self._queryDB.connection.commit()
        self._queryDB.connection.close()

    def new_reply(self, object_name, message, create_date, author, new_price, origin_price, permalink):
        """
        Replies a second time to the user after a set amount of time
        """ 
        """
        print(self._replyMessage.format(
                message,
                object_name
            ))
        """
        print("---------------")
        print(author)
        print(object_name)

        origin_date_text = ""
        origin_date_text =  ("\n\nYou requested this reminder on: " 
                            "[" + _force_utf8(create_date) + " UTC](http://www.wolframalpha.com/input/?i="
                             + _force_utf8(create_date) + " UTC To Local Time)")

        high_time = datetime.utcfromtimestamp(self._high_time)
        high_time_formatted = ("[" + _force_utf8(format(high_time, '%Y-%m-%d %H:%M:%S')) + " UTC](http://www.wolframalpha.com/input/?i="
                             + _force_utf8(format(high_time, '%Y-%m-%d %H:%M:%S')) + " UTC To Local Time)")

        low_time = datetime.utcfromtimestamp(self._low_time)
        low_time_formatted = ("[" + _force_utf8(format(low_time, '%Y-%m-%d %H:%M:%S')) + " UTC](http://www.wolframalpha.com/input/?i="
                             + _force_utf8(format(low_time, '%Y-%m-%d %H:%M:%S')) + " UTC To Local Time)")

        try:
            reddit.redditor(str(author)).message('Hello, ' + _force_utf8(str(author)) + ' RemindMeBot Here!', self._replyMessage.format(
                    message=_force_utf8(message),
                    original=_force_utf8(permalink),
                    parent= self.parent_comment(object_name),
                    origin_date_text = origin_date_text,
                    new_price = '${:,.2f}'.format(new_price),
                    origin_price = '${:,.2f}'.format(origin_price),
                    price = '${:,.2f}'.format(self._low if new_price <= origin_price else self._high),
                    price_time = low_time_formatted if new_price <= origin_price else high_time_formatted
                ))
            print("Did It")
            return True
        except APIException as err:
            print("APIException", err)
            return False
        except IndexError as err:
            print("IndexError", err)
            return False
        except (HTTPError, ConnectionError, Timeout, timeout) as err:
            print("HTTPError", err)
            time.sleep(10)
            return False
        except ClientException as err:
            print("ClientException", err)
            time.sleep(10)
            return False
        except PRAWException as err:
            print("PRAWException", err)
            time.sleep(10)
            return False


def _force_utf8(text):
    return str(text).encode('utf-8')


# =============================================================================
# MAIN
# =============================================================================

def main():
    while True:
        checkReply = Reply()
        checkReply.set_interval_extremes()
        checkReply.time_to_reply()
        checkReply.search_db()

        #dont let 0 get into the lastrun.txt. It breaks the api call to get the prices
        if not checkReply._last_price_time:
            checkReply._last_price_time = 10000

        lastrun_file = open("lastrun.txt", "w")
        lastrun_file.write(str(checkReply._last_price_time))
        lastrun_file.close()

        time.sleep(600)


# =============================================================================
# RUNNER
# =============================================================================
print("start")
if __name__ == '__main__':
    main()