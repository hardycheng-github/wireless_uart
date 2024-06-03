#!/bin/bash
cd "$(dirname $0)"

python3 ../../../esp8266/ESP8266_RTOS_SDK/components/esptool_py/esptool/esptool.py \
--chip esp8266 \
--port /dev/ttyUSB0 \
--baud 115200 \
--before default_reset \
--after hard_reset write_flash -z \
--flash_mode dio \
--flash_freq 40m \
--flash_size 4MB 0xd000 ota_data_initial.bin 0x0 bootloader/bootloader.bin 0x10000 wireless-uart.bin 0x8000 partitions_two_ota.bin
