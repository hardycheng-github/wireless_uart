DEV_PATH="/shares/develop";
TARGET_PATH="/shares/fw_lastest";
echo "TARGET_PATH=$TARGET_PATH";
mkdir -p ${TARGET_PATH}/bootloader;
git reset --hard;
git pull;

./install.sh;
. ./export.sh;

# if develop exists, replace it
if [ -e $DEV_PATH ]; then
    echo "DEV_PATH=$DEV_PATH exists, start develop build!";
    if [ -e develop_bak ]; then
        rm -r develop_bak;
    fi
    mv develop develop_bak;
    cp -r $DEV_PATH develop;
fi

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

if [ -e $DEV_PATH ]; then
    rm -r develop;
    mv develop_bak develop;
    rm -r $DEV_PATH;
fi