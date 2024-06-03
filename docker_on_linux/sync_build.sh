if [ -e build.sh ]; then
    rm build.sh;
fi
cp /shares/resources/build.sh build.sh;
chmod 755 build.sh;
./build.sh;