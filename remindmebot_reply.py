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
                     user_agent='cryptoRemindMe by /u/boyAndHisBlob',
                     username=bot_username)
# DB Info
DB_USER = config.get("SQL", "user")
DB_PASS = config.get("SQL", "passwd")

supported_tickers = ["ADA","BCH","BCN","BTC","BTG","DASH","ETC","ETH","LSK","LTC","MIOTA","NEO","QTUM","STEEM","XEM","XLM","XMR","XRB","XRP","ZEC"]

# =============================================================================
# CLASSES
# =============================================================================

class DbConnectiton(object):
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

class Reply(object):

    def __init__(self):
        self._db_connection = DbConnectiton()
        self._replyMessage =(
            "cryptoRemindMeBot private message here!" 
            "\n\n**The message:** \n\n>{message}"
            "\n\n**The original comment:** \n\n>{original}"
            "\n\n**The parent comment from the original comment or its submission:** \n\n>{parent}"
            "{origin_date_text}"
            "\n\nYou requested a reminder when the price reached {new_price} from {origin_price}."
            "\n\nThe price hit {price} at {price_time} using CryptoCompare's Current Aggregate."
            "\n\n_____\n\n"
            "|[^(FAQs)](http://np.reddit.com/r/RemindMeBot/comments/24duzp/remindmebot_info/)"
            "|[^(Your Reminders)](http://np.reddit.com/message/compose/?to=cryptoRemindMeBot&subject=List Of Reminders&message=MyReminders!)"
            "|[^(Feedback)](http://np.reddit.com/message/compose/?to=boyAndHisBlob&subject=cryptoRemindMe Feedback)"
            "|[^(Code)](https://github.com/jjmerri/cryptoRemindMe-Reddit)"
            "\n|-|-|-|-|-|-|"
            )
        self._high = 0.00
        self._low = 100000.00
        self.last_price_time = 0
        self._price_history = {}


    def set_price_extremes(self):
        """
        Sets the high and low since the last run
        """

        lastrun_file = open("lastrun.txt", "r")
        lastrun_sec = int(lastrun_file.read())

        lastrun_file.close()

        for supported_ticker in supported_tickers:
            current_time_sec = int(time.time())
            mins_since_lastrun = (current_time_sec - lastrun_sec) // 60
            r = requests.get('https://min-api.cryptocompare.com/data/histominute?fsym={ticker}&tsym=USD&e=CCCAGG&limit='.format(ticker=supported_ticker) + str(mins_since_lastrun))
            response = r.json()
            self._price_history[supported_ticker] = response['Data']

            for minute_data in self._price_history[supported_ticker]:

                high = minute_data['high']
                low = minute_data['low']

                if self._price_history[supported_ticker + "_high"] is None or high > self._price_history[supported_ticker + "_high"]:
                    self._price_history[supported_ticker + "_high"] = high
                    self._price_history[supported_ticker + "_high_time"] = minute_data['time']

                if self._price_history[supported_ticker + "_low"] is None or low < self._price_history[supported_ticker + "_low"]:
                    self._price_history[supported_ticker + "_low"] = low
                    self._price_history[supported_ticker + "_low_time"] = minute_data['time']

                if minute_data['time'] > self.last_price_time:
                    self.last_price_time = minute_data['time']


    def _parent_comment(self, commentId):
        """
        Returns the parent comment or if it's a top comment
        return the original submission
        """
        try:
            comment = reddit.comment(id=commentId)
            if comment.is_root:
                return comment.submission.permalink
            else:
                return comment.parent().permalink
        except IndexError as err:
            print("parrent_comment error")
            return "It seems your original comment was deleted, unable to return parent comment."
        # Catch any URLs that are not reddit comments
        except Exception  as err:
            print(err)
            print("HTTPError/PRAW parent comment")
            return "Parent comment not required for this URL."

    def populate_reply_list(self):
        """
        Checks to see through SQL if net_date is < current time
        """
        cmd = "SELECT * FROM reminder WHERE (new_price <= %s AND new_price >= origin_price) OR (new_price >= %s AND new_price <= origin_price)"
        self._db_connection.cursor.execute(cmd, [self._high, self._low])

    def send_replies(self):
        """
        Loop through data looking for which comments are old
        """

        data = self._db_connection.cursor.fetchall()
        already_commented = []
        for row in data:
            # checks to make sure ID hasn't been commented already
            # For situtations where errors happened
            if row[0] not in already_commented:
                # MySQl- object_name, message, create date, reddit user, new_price, origin_price
                delete_message = self._send_reply(row[1], row[2], str(row[6]), row[5], row[3], row[4], row[8])
                if delete_message:
                    cmd = "DELETE FROM reminder WHERE id = %s"
                    self._db_connection.cursor.execute(cmd, [row[0]])
                    self._db_connection.connection.commit()
                    already_commented.append(row[0])

        self._db_connection.connection.commit()
        self._db_connection.connection.close()

    def _send_reply(self, object_name, message, create_date, author, new_price, origin_price, permalink):
        """
        Replies a second time to the user after a set amount of time
        """
        print("---------------")
        print(author)
        print(object_name)

        origin_date_text = ""
        origin_date_text =  ("\n\nYou requested this reminder on: " 
                            "[" + create_date + " UTC](http://www.wolframalpha.com/input/?i="
                             + create_date + " UTC To Local Time)")

        high_time = datetime.utcfromtimestamp(self._high_time)
        high_time_formatted = ("[" + format(high_time, '%Y-%m-%d %H:%M:%S') + " UTC](http://www.wolframalpha.com/input/?i="
                             + format(high_time, '%Y-%m-%d %H:%M:%S') + " UTC To Local Time)")

        low_time = datetime.utcfromtimestamp(self._low_time)
        low_time_formatted = ("[" + format(low_time, '%Y-%m-%d %H:%M:%S') + " UTC](http://www.wolframalpha.com/input/?i="
                             + format(low_time, '%Y-%m-%d %H:%M:%S') + " UTC To Local Time)")

        try:
            reddit.redditor(str(author)).message('Hello, ' + str(author) + ' RemindMeBot Here!', self._replyMessage.format(
                    message=message,
                    original=permalink,
                    parent= self._parent_comment(object_name),
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


# =============================================================================
# MAIN
# =============================================================================

def main():
    while True:
        checkReply = Reply()
        checkReply.set_price_extremes()
        checkReply.populate_reply_list()
        checkReply.send_replies()

        #dont let 0 get into the lastrun.txt. It breaks the api call to get the prices
        if not checkReply.last_price_time:
            checkReply.last_price_time = 10000

        lastrun_file = open("lastrun.txt", "w")
        lastrun_file.write(str(checkReply.last_price_time))
        lastrun_file.close()

        time.sleep(600)


# =============================================================================
# RUNNER
# =============================================================================
print("start")
if __name__ == '__main__':
    main()