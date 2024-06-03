#!/bin/bash

script_file=$(realpath "${BASH_SOURCE[0]}")
script_dir=$(dirname "$script_file")
cd $script_dir

cp -r ../esp8266/ESP8266_RTOS_SDK/develop shares/develop

bash 2_build_with_esp8266.sh
bash 3_update_fw.sh
