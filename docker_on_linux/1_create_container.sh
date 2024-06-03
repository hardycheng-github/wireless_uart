#!/bin/bash
echo $PWD/shares
docker container create -it -v $PWD/shares:/shares --name esp8266 esp8266 bash