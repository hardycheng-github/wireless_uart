@echo off
setlocal enabledelayedexpansion

xcopy "../esp8266/ESP8266_RTOS_SDK/develop" "shares/develop" /s /e /y /i

call 2_build_with_esp8266.bat
call 3_update_fw.bat
