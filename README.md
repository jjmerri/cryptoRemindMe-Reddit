# Crypto Remind Me Reddit Bot

## User Guide

#### What is the point of cryptoRemindMeBot?

cryptoRemindMeBot was made as a way to remind the user about a comment or thread for later use when a price is hit for a given cryptocurrency. For example, someone on /r/ripple makes a commment that they are going to go streaking in the streets when the price of XRP reaches $2. You can make a comment with the command "cryptoRemindMe! XRP $2" and you will get a PM from cryptoRemindMeBot reminding you of the commment when the price of XRP reaches $2. All price data is pulled using the CryptoCompare api.

#### Supported Cryptocurrency Tickers

["ADA","BCH","BCN","BTC","BTG","DASH","DOGE","ETC","ETH","LSK","LTC","NEO","QASH","QTUM","REQ","STEEM","XEM","XLM","XMR","XRB","XRP","ZEC"]

#### Commands
##### cryptoRemindMe! {ticker} {price} {optional_message}
This is the main command that the cryptoRemindMeBot processes. It can be sent to the bot as a PM or can be made as a comment. The cryptoRemindMeBot user will send you a PM when the cryptocurrency specified by the ticker reaches the price you specified.

Example:

cryptoRemindMe! xrp $2.10 "Some reason for reminder"

##### Delete! {comment_id}
The Delete command can only be initiated through a PM to cryptoRemindMeBot. It will delete the confirmation comment made by the cryptoRemindMeBot Reddit user. This will only work if the user making the request is the user the bot replied to. A link containing this command is provided in all cryptoRemindMeBot confirmation comments.

Example:

Delete! dtyp8av

##### MyReminders!
The MyReminders command can only be initiated through a PM to cryptoRemindMeBot. It will cause the bot to reply to your PM with a list of your current reminders that have not yet been fulfilled.


Example:

MyReminders!

##### Remove! {reminder_id}
The Remove command can only be initiated through a PM to cryptoRemindMeBot. It will cause the bot to remove the reminder that corresponds to the given reminder_id. You can only remove reminders if you requested the reminder. A link to this command will be provided in the list of current reminders provided by the MyReminders command.


Example:

Remove! 99

##### RemoveAll!
The RemoveAll command can only be initiated through a PM to cryptoRemindMeBot. It will cause the bot to remove all reminders for the user making the request.


Example:

RemoveAll!


## Technical Stuff

#### Version Requirements

Python = 3.6.4

PRAW = 5.4

#### Configuration

remindmebot.cfg contains all usernames and passwords as well as environment specific configurations needed to run the Python scripts. When the environment is set to DEV some functionality is turned off in order to avoid processing real data. When the environment is set to DEV the .running files will be removed before startup. It is expected that your DEV database is different than your production database.

#### External Dependencies

* [Reddit via PRAW](http://praw.readthedocs.io/en/latest/index.html) - The method of all the interactions with the users

* [Pushshift API](https://github.com/pushshift/api) - Used to search for comments to be processed

* [CryptoCompare API](https://www.cryptocompare.com/api/) - Used to get price data

#### remindmebot_search.py

This script is responsible for finding comments and PMs that should be processed by the bot. If the  comment or PM is a reminder then it will save the reminder in the database and send a confirmation reply to the user who set the reminder. If the PM was not a reminder but another supported command such as DeleteAll! then the PM is processed immediately and a confirmation reply is sent.

On startup this script checks for a search_bot.running file and if found, immediately terminates to prevent multiple instances from running in parallel. If no .running file is found then it creates one and begins normal processing. It will stay running until the .running file is removed at which time it will shut down gracefully.

#### remindmebot_reply.py

This script checks the prices of supported cryptocurrencies and sends a reminder when necessary based on the reminder info stored in the database. When a reminder is sent it is removed from the database.

On startup this script checks for a reply_bot.running file and if found, immediately terminates to prevent multiple instances from running in parallel. If no .running file is found then it creates one and begins normal processing. It will stay running until the .running file is removed at which time it will shut down gracefully.

#### restart_crypto_remind_me_bot.sh

This Bash script will gracefully stop running instances of the Python scripts by removing their .running files and then it will start new instances of the scripts.

#### lastrun files

These files are updated by the Python scripts to persist timestamps of when processes are run. This allows the bots to pick up where they left of chronologically in the event of a restart. The timestamps are used to retrieve price data as well as unprocessed comments. The information in these files will eventually be moved to a table in the database.

#### schema.sql

This file contains the database schema. It is to be run only on database initialization to create the necessary objects. It drops the current database if it exists so it should never be run in production except on database creation.

#### Database

A MySql database with the following objects:

* Tables
	* reminder - contains all the reminder requests.


#### Thanks to SIlver who created the original RemindMe Reddit Bot and inspired this project.
Base code was copied from https://github.com/SIlver--/remindmebot-reddit then upgraded to use current versions of PRAW and Python.
