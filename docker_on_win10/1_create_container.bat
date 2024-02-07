echo %cd%/shares
docker container create -it -v %cd%/shares:/shares --name esp8266 esp8266 bash