#!/bin/bash

script_file=$(realpath "${BASH_SOURCE[0]}")
script_dir=$(dirname "$script_file")
cd $script_dir

docker build --no-cache --tag esp8266 .
# docker build --tag esp8266 .