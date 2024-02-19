TARGET_PATH="/shares/fw_lastest";
echo "TARGET_PATH=$TARGET_PATH";
mkdir -p ${TARGET_PATH}/bootloader;
git pull;
./install.sh;
. ./export.sh;
cd develop/app/wireless_uart/;
echo "cd %~dp0" > ${TARGET_PATH}/esptool.bat;
make all | tail -n 1 | grep bootloader >> ${TARGET_PATH}/esptool.bat;
sed -i \
-e 's!/esp/git/ESP8266_RTOS_SDK/develop/app/wireless_uart/build/!!g' \
-e 's!/esp/git/!../../../esp8266/!g' \
-e 's!--!^\n--!g' \
${TARGET_PATH}/esptool.bat;

cp -r build/**.bin $TARGET_PATH/;
cp -r build/bootloader/**.bin ${TARGET_PATH}/bootloader/;
