cd "$(dirname "$0")"
CUR_PATH="$(pwd)"
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
    echo "backup original develop folder...";
    find develop -type d -name build -prune -o -type f -print0 | while IFS= read -r -d '' file; do
        target=${file//develop\//develop_bak\/}
        target_path="$(dirname $target)"
        mkdir -p $target_path
        cp $file $target_path
        echo " - backup develop file: $target"
    done
    echo "start moving the lastest develop files...";
    find $DEV_PATH -type d -name build -prune -o -type f -print0 | while IFS= read -r -d '' file; do
        file="$(readlink -f $file)"
        target="develop/${file#"$DEV_PATH/"}"
        target_md5="$(md5sum $target | awk '{print $1}' | uniq)"
        file_md5="$(md5sum $file | awk '{print $1}' | uniq)"
        target_path="$(dirname $target)"
        if [ "$target_md5" != "$file_md5" ]; then
            mkdir -p $target_path
            cp $file $target_path
            echo " - backup develop file: $target"
            echo "  |_ old md5: $target_md5"
            echo "  |_ new md5: $file_md5"
        fi
    done
fi

echo "start build...";
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
    echo "restore original develop folder...";
    cd $CUR_PATH;
    find develop_bak -type d -name build -prune -o -type f -print0 | while IFS= read -r -d '' file; do
        target=${file//develop_bak\//develop\/}
        target_md5="$(md5sum $target | awk '{print $1}' | uniq)"
        file_md5="$(md5sum $file | awk '{print $1}' | uniq)"
        target_path="$(dirname $target)"
        if [ "$target_md5" != "$file_md5" ]; then
            mkdir -p $target_path
            cp $file $target_path
            echo " - restore develop file: $target"
        fi
    done
    rm -r $DEV_PATH;
fi

echo "done!";