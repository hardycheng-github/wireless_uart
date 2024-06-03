#!/bin/bash

script_file=$(realpath "${BASH_SOURCE[0]}")
script_dir=$(dirname "$script_file")
cd $script_dir

echo $script_dir/shares
docker container create -it -v $script_dir/shares:/shares --name esp8266 esp8266 bash
