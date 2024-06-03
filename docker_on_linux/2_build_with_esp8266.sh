#!/bin/bash

script_file=$(realpath "${BASH_SOURCE[0]}")
script_dir=$(dirname "$script_file")
cd $script_dir

docker start esp8266
docker exec esp8266 bash sync_build.sh
