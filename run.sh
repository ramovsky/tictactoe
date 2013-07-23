#!/bin/bash

stop(){
    echo 'Killing'
    for p in $(ps ax |grep python |grep router |cut -d " " -f 1); do kill $p; done;
    for p in $(ps ax |grep python |grep game |cut -d " " -f 1); do kill $p; done;
    killall python;
    echo 'Bye'
    exit 9
}

python -m tictactoe.game --port=8881 --redis_host=localhost --redis_port=6379 &
python -m tictactoe.game --port=8882 --redis_host=localhost --redis_port=6379 &
python -m tictactoe.router --port=8889 --game=localhost:8881,localhost:8882 --redis_host=localhost --redis_port=6379 &

trap 'stop' SIGINT

while true ; do
    read x
done
