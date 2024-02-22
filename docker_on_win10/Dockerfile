FROM ubuntu:18.04

ENV ESP_ROOT=/esp
RUN apt update
RUN apt install curl gcc git wget make libncurses-dev flex bison gperf python python-pip python-setuptools python-serial python-cryptography python-future python-pyparsing python3 python3-pip libffi-dev libssl-dev busybox socat -y
RUN pip3 install pyserial
RUN mkdir -p $ESP_ROOT
RUN cd $ESP_ROOT

# setup sdk from git
ENV ESP_GIT_ROOT=$ESP_ROOT/git
ENV ESP_WUART_URL=https://github.com/hardycheng-github/wireless_uart.git
ENV ESP_WUART_PATH=$ESP_GIT_ROOT/wireless_uart
ENV ESP_SDK_ROOT=$ESP_ROOT/sdk
ENV ESP_SDK_PATH=$ESP_SDK_ROOT/ESP8266_RTOS_SDK
RUN mkdir -p $ESP_GIT_ROOT
RUN cd $ESP_GIT_ROOT
RUN git clone --recurse-submodules $ESP_WUART_URL $ESP_WUART_PATH
RUN mkdir -p $ESP_SDK_ROOT
RUN ln -s $ESP_WUART_PATH/esp8266/ESP8266_RTOS_SDK $ESP_SDK_PATH
RUN cd $ESP_SDK_PATH
WORKDIR $ESP_SDK_PATH
RUN $ESP_SDK_PATH/install.sh
COPY sync_build.sh ./