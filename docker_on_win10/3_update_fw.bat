@echo off
setlocal enabledelayedexpansion

set "file=shares/fw_lastest/esptool.bat"
set "tempfile=temp.bat"

set "searchString=--port"

for /f "tokens=1,2 delims= " %%i in (%file%) do (
    set "param=%%i"
	set "value=%%j"
	if "!param!" == "--port" (
		set "original_port=%%j"
	)
)

if "%original_port%" == "" (
	echo esptool script not found...
	pause
	exit
)

echo original port=%original_port%
set /p new_port=Enter new port (e.g., COM3): 

if "%new_port%" neq "" (
	rem 替换 --port 参数内容为新端口
	(for /f "delims=" %%i in (%file%) do (
		set "line=%%i"
		set "line=!line:%original_port%=%new_port%!"
		echo !line!
	)) > %tempfile%
	
	move /y %tempfile% %file%

	echo Port updated successfully.
)

echo Start update firmware...

call %file%

pause