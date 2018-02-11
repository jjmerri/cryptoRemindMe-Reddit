#!/usr/bin/env python3.6

# =============================================================================
# IMPORTS
# =============================================================================

import praw
import MySQLdb
import configparser
import time
import requests
import logging
from datetime import datetime
from requests.exceptions import HTTPError, ConnectionError, Timeout
from praw.exceptions import APIException, ClientException, PRAWException
from socket import timeout

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
                     user_agent='cryptoRemindMe by /u/BoyAndHisBlob',
                     username=bot_username)
# DB Info
DB_USER = config.get("SQL", "user")
DB_PASS = config.get("SQL", "passwd")

FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger('cryptoRemindMeBot')
logger.setLevel(logging.INFO)

supported_tickers = ["ADA","BCH","BCN","BTC","BTG","DASH","DOGE","ETC","ETH","LSK","LTC","NEO","QASH","QTUM","STEEM",
                     "XEM","XLM","XMR","XRB","XRP","ZEC"]

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
            "\n\nYou requested a reminder when the price of {ticker} reached {new_price} from {origin_price}."
            "\n\nThe price hit {price} at {price_time} using CryptoCompare's Current Aggregate."
            "\n\n_____\n\n"
            "|[^(README)](https://github.com/jjmerri/cryptoRemindMe-Reddit/blob/master/README.md)"
            "|[^(Your Reminders)](http://np.reddit.com/message/compose/?to=cryptoRemindMeBot&subject=List Of Reminders&message=MyReminders!)"
            "|[^(Feedback)](http://np.reddit.com/message/compose/?to=BoyAndHisBlob&subject=cryptoRemindMe Feedback)"
            "|[^(Code)](https://github.com/jjmerri/cryptoRemindMe-Reddit)"
            "\n|-|-|-|-|-|-|\n\n" +
            "^^^^.\n\n^^^^**DISCLAIMER:** ^^^^The ^^^^developer ^^^^that ^^^^maintains ^^^^this ^^^^bot ^^^^does ^^^^not ^^^^guarantee ^^^^the ^^^^accuracy ^^^^of ^^^^the ^^^^data ^^^^it ^^^^provides ^^^^nor ^^^^does ^^^^he ^^^^gurantee ^^^^the ^^^^reliability ^^^^of ^^^^its ^^^^notification ^^^^system. ^^^^Do ^^^^not ^^^^rely ^^^^on ^^^^this ^^^^bot ^^^^for ^^^^information ^^^^that ^^^^will ^^^^affect ^^^^your ^^^^financial ^^^^decisions. ^^^^Double ^^^^check ^^^^all ^^^^prices ^^^^before ^^^^acting ^^^^on ^^^^any ^^^^information ^^^^provided ^^^^by ^^^^this ^^^^bot. ^^^^Do ^^^^not ^^^^rely ^^^^solely ^^^^on ^^^^this ^^^^bot ^^^^to ^^^^notify ^^^^you ^^^^of ^^^^price ^^^^updates ^^^^as ^^^^it ^^^^doesn't ^^^^have ^^^^failsafes ^^^^in ^^^^place ^^^^to ^^^^be ^^^^100% ^^^^reliable."
            )
        self.last_price_time = {}
        self._price_history = {}


    def set_price_extremes(self):
        """
        Sets the high and low since the last run
        """

        lastrun_file = open("lastrun.txt", "r")
        lastrun_sec = {}
        for lastrun in lastrun_file.read().splitlines():
            values = lastrun.split(" ")
            if len(values) == 2:
                lastrun_sec[values[0]] = int(values[1])

        lastrun_file.close()

        for supported_ticker in supported_tickers:
            current_time_sec = int(time.time())
            if supported_ticker in lastrun_sec:
                mins_since_lastrun = (current_time_sec - lastrun_sec[supported_ticker]) // 60
            else:
                #max allowed by API
                mins_since_lastrun = 2000

            #Get data from at least 10 min back
            mins_since_lastrun = mins_since_lastrun if mins_since_lastrun >= 10 else 10

            r = requests.get('https://min-api.cryptocompare.com/data/histominute?fsym={ticker}&tsym=USD&e=CCCAGG&limit='.format(ticker=supported_ticker) + str(mins_since_lastrun))
            response = r.json()
            self._price_history[supported_ticker] = response['Data']

            for minute_data in self._price_history[supported_ticker]:

                high = minute_data['high']
                low = minute_data['low']

                if (supported_ticker + "_high") not in self._price_history or high > self._price_history[supported_ticker + "_high"]:
                    self._price_history[supported_ticker + "_high"] = high
                    self._price_history[supported_ticker + "_high_time"] = minute_data['time']

                if (supported_ticker + "_low") not in self._price_history or low < self._price_history[supported_ticker + "_low"]:
                    self._price_history[supported_ticker + "_low"] = low
                    self._price_history[supported_ticker + "_low_time"] = minute_data['time']

                if supported_ticker not in self.last_price_time or minute_data['time'] > self.last_price_time[supported_ticker]:
                    self.last_price_time[supported_ticker] = minute_data['time']


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
            logger.error("parrent_comment error")
            return "It seems your original comment was deleted, unable to return parent comment."
        # Catch any URLs that are not reddit comments
        except Exception  as err:
            logger.error(err)
            logger.error("HTTPError/PRAW parent comment")
            return "Parent comment not required for this URL."

    def populate_reply_list(self):
        """
        Checks to see through SQL if net_date is < current time
        """
        select_statement = "SELECT * FROM reminder WHERE "
        single_where_clause = "(new_price <= %s AND new_price >= origin_price AND ticker = %s) OR (new_price >= %s AND new_price <= origin_price AND ticker = %s)"
        where_clause = ((single_where_clause + " OR ") * len(supported_tickers))[0:-4]
        cmd = select_statement + where_clause

        cmd_args = []

        for supported_ticker in supported_tickers:
            if (supported_ticker + "_high") in self._price_history and (supported_ticker + "_low") in self._price_history:
                cmd_args.append(self._price_history[supported_ticker + "_high"])
                cmd_args.append(supported_ticker)
                cmd_args.append(self._price_history[supported_ticker + "_low"])
                cmd_args.append(supported_ticker)
            else:
                #remove a where clause + " AND "
                cmd_minus_where_length = len(single_where_clause) + 4
                cmd = cmd[:(cmd_minus_where_length * -1)]

        self._db_connection.cursor.execute(cmd, cmd_args)

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
                ticker = row[9]
                object_name = row[1]
                new_price = row[3]
                origin_price = row[4]
                comment_create_datetime = row[10]

                send_reply = False
                message_price = 0.0
                message_price_time = 0

                try:
                    for minute_data in self._price_history[ticker]:
                        price_high = minute_data['high']
                        price_low = minute_data['low']
                        price_time = minute_data['time']

                        if price_time >= comment_create_datetime.timestamp():
                            if new_price <= price_high and new_price >= origin_price:
                                message_price = price_high
                            elif new_price >= price_low and new_price <= origin_price:
                                message_price = price_low
                            else:
                                # This is not the minute_data that triggered the reply
                                continue

                            message_price_time = price_time
                            send_reply = True
                            break

                except IndexError as err:
                    logger.error(err)
                    logger.error("IndexError in send_replies")
                    send_reply = False
                # Catch any URLs that are not reddit comments
                except Exception  as err:
                    logger.error(err)
                    logger.error("Unknown Exception send_replies")
                    send_reply = False

                if send_reply:
                    # MySQl- object_name, message, comment_create_datetime, reddit user, new_price, origin_price, permalink, ticker, message_price_time, message_price
                    delete_message = self._send_reply(object_name, row[2], comment_create_datetime, row[5], new_price, origin_price, row[8], ticker, message_price_time, message_price)
                    if delete_message:
                        cmd = "DELETE FROM reminder WHERE id = %s"
                        self._db_connection.cursor.execute(cmd, [row[0]])
                        self._db_connection.connection.commit()
                        already_commented.append(row[0])

        self._db_connection.connection.commit()
        self._db_connection.connection.close()

    def _send_reply(self, object_name, message, comment_create_datetime, author, new_price, origin_price, permalink, ticker, message_price_time, message_price):
        """
        Replies a second time to the user after a set amount of time
        """
        logger.info("---------------")
        logger.info(author)
        logger.info(object_name)

        utc_create_date_str = str(datetime.utcfromtimestamp(comment_create_datetime.timestamp()))
        origin_date_text =  ("\n\nYou requested this reminder on: " 
                            "[" + utc_create_date_str + " UTC](http://www.wolframalpha.com/input/?i="
                             + utc_create_date_str + " UTC To Local Time)")

        message_price_datetime = datetime.utcfromtimestamp(message_price_time)
        message_price_datetime_formatted = ("[" + format(message_price_datetime, '%Y-%m-%d %H:%M:%S') + " UTC](http://www.wolframalpha.com/input/?i="
                             + format(message_price_datetime, '%Y-%m-%d %H:%M:%S') + " UTC To Local Time)")

        try:
            reddit.redditor(str(author)).message('cryptoRemindMeBot Reminder!', self._replyMessage.format(
                    message=message,
                    original=permalink,
                    parent= self._parent_comment(object_name),
                    origin_date_text = origin_date_text,
                    new_price = '${:,.4f}'.format(new_price),
                    origin_price = '${:,.4f}'.format(origin_price),
                    price = '${:,.4f}'.format(message_price),
                    price_time = message_price_datetime_formatted,
                    ticker = ticker
                ))
            logger.info("Sent Reply")
            return True
        except APIException as err:
            logger.error(err)
            logger.error("APIException in _send_reply")
            return False
        except IndexError as err:
            logger.error(err)
            logger.error("IndexError in _send_reply")
            return False
        except (HTTPError, ConnectionError, Timeout, timeout) as err:
            logger.error(err)
            logger.error("HTTPError in _send_reply")
            time.sleep(10)
            return False
        except ClientException as err:
            logger.error(err)
            logger.error("ClientException in _send_reply")
            time.sleep(10)
            return False
        except PRAWException as err:
            logger.error(err)
            logger.error("PRAWException in _send_reply")
            time.sleep(10)
            return False
        except Exception as err:
            logger.error(err)
            logger.error("Unknown Exception in _send_reply")
            return False

def update_last_run(checkReply):
    lastrun_tickers = ""
    for supported_ticker in supported_tickers:
        # dont let 0 get into the lastrun.txt. It breaks the api call to get the prices
        if supported_ticker not in checkReply.last_price_time:
            checkReply.last_price_time[supported_ticker] = 10000

        lastrun_tickers += supported_ticker + " " + str(
            checkReply.last_price_time.get(supported_ticker, "10000")) + "\n"

    lastrun_file = open("lastrun.txt", "w")
    lastrun_file.write(lastrun_tickers)
    lastrun_file.close()

# =============================================================================
# MAIN
# =============================================================================

def main():
    while True:
        logger.info("Start Main Loop")
        checkReply = Reply()
        checkReply.set_price_extremes()
        checkReply.populate_reply_list()
        checkReply.send_replies()

        update_last_run(checkReply)

        logger.info("End Main Loop")
        time.sleep(600)


# =============================================================================
# RUNNER
# =============================================================================
logger.info("start")
if __name__ == '__main__':
    main()