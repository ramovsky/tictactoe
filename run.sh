#!/bin/bash

stop(){
    echo 'Killing'
    for p in $(ps ax |grep python |grep router |cut -d " " -f 1); do kill $p; done;
    for p in $(ps ax |grep python |grep game |cut -d " " -f 1); do kill $p; done;
    echo 'Bye'
    exit 9
}

python -m tictactoe.game --port=8881 --redis_host=localhos --redis_port=6379 &
python -m tictactoe.game --port=8882 --redis_host=localhos --redis_port=6379 &
python -m tictactoe.router --port=8888 --game=g1.tic.tac:8881,g2.tic.tac:8882 --domain=.tic.tac --redis_host=localhos --redis_port=6379 &

trap 'stop' SIGINT

while true ; do
    read x
done
