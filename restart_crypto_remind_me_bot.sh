#!/bin/bash
script_dir="/root/apps/cryptoRemindMe-Reddit/"
logs_dir=$script_dir"logs/"
search_running_file=$script_dir"search_bot.running"
reply_running_file=$script_dir"reply_bot.running"

search_log_file="search.log"
reply_log_file="reply.log"

search_pid=`cat $search_running_file`
reply_pid=`cat $reply_running_file`

rm $search_running_file
rm $reply_running_file

kill -0 $search_pid
kill_search_ret=$?

kill -0 $reply_pid
kill_reply_ret=$?

while [ $kill_reply_ret -eq 0 -o $kill_search_ret -eq 0 ]
do
    echo "PIDs $search_pid $reply_pid still running. Sleep for 60 secs"
    sleep 60

    kill -0 $search_pid
    kill_search_ret=$?

    kill -0 $reply_pid
    kill_reply_ret=$?
done

echo "renaming logs"
mv $script_dir$search_log_file $logs_dir$search_log_file.$(date +%F-%T)
mv $script_dir$reply_log_file $logs_dir$reply_log_file.$(date +%F-%T)

echo "PIDs stopped. Starting scripts."

python3 -u $script_dir"remindmebot_search.py" > $script_dir$search_log_file 2>&1 &
search_pid=$!

python3 -u $script_dir"remindmebot_reply.py" > $script_dir$reply_log_file 2>&1 &
reply_pid=$!

echo "disowning $search_pid $reply_pid"
disown $search_pid $reply_pid

echo "complete"