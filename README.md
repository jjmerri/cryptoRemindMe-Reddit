# Crypto Remind Me Reddit Bot

#### What is the point of cryptoRemindMeBot?

cryptoRemindMeBot was made as a way to remind the user about a comment or thread for later use when a price is hit for a given cryptocurrency. For example, someone on /r/ripple makes a commment that they are going to go streaking in the streets when the price of XRP reaches $2. You can make a comment with the command "cryptoRemindMe! XRP $2" and you will get a PM from cryptoRemindMeBot when the price of XRP reaches $2. All price data is pulled using the CryptoCompare api.

#### Supported Cryptocurrency Tickers

["ADA","BCH","BCN","BTC","BTG","DASH","ETC","ETH","LSK","LTC","NEO","QTUM","STEEM","XEM","XLM","XMR","XRB","XRP","ZEC"]

#### Commands
##### cryptoRemindMe! {ticker} {price} {optional_message}
This is the main command that the cryptoRemindMeBot processes. It can be sent to the bot as a PM or can be made as a comment. The cryptoRemindMeBot user will send you a PM when the cryptocurrency specified by the ticker reaches the price you specified.

Example:

cryptoRemindMe! xrp $2.10 "Some reason for reminder"

##### Delete! {comment_id}
The Delete command can only be initiated through a PM to cryptoRemindMeBot. It will delete the confirmation comment made by the cryptoRemindMeBot Reddit user. This will only work if the user making the request is the user the bot replied to. I link containing this command is provided in all cryptoRemindMeBot confirmation comments.

Example:

Delete! dtyp8av

##### MyReminders!
The MyReminders command can only be initiated through a PM to cryptoRemindMeBot. It will cause the bot to reply to your PM with a list of your current reminders that have not yet been fulfilled.


Example:

MyReminders!

##### Remove! {reminder_id}
The Remove command can only be initiated through a PM to cryptoRemindMeBot. It will cause the bot to remove the reminder that corresponds to the given reminder_id. You can only remove reminders you requested the reminder. A link to this command will be provided in the list of current reminders provided by the MyReminders command.


Example:

Remove! 99

##### RemoveAll!
The Remove command can only be initiated through a PM to cryptoRemindMeBot. It will cause the bot to remove all reminders for the user making the request.


Example:

RemoveAll!


#### Thanks to SIlver who created the original RemindMe Reddit Bot and inspired this project.
Base code was copied from https://github.com/SIlver--/remindmebot-reddit then upgraded to use current versions of PRAW and Python.
