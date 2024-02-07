TARGET_PATH="/shares/fw_lastest";
echo "TARGET_PATH=$TARGET_PATH";
mkdir -p ${TARGET_PATH}/bootloader;
git pull;
./install.sh;
. ./export.sh;
cd develop/app/wireless_uart/;
make all | tail -n 1 | grep bootloader > ${TARGET_PATH}/esptool.bat;

cp -r build/**.bin $TARGET_PATH/;
cp -r build/bootloader/**.bin ${TARGET_PATH}/bootloader/;
