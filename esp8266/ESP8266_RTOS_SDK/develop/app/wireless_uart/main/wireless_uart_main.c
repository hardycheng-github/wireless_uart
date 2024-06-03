#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_system.h"
#include "esp_spi_flash.h"
#include "driver/uart.h"
#include "wuart_utils.h"

static uint8_t mac_addr[6];

void setup_uart(int baud_rate, int buf_size){
    // Configure parameters of an UART driver,
    // communication pins and install the driver
    uart_config_t uart_config = {
        .baud_rate = baud_rate,
        .data_bits = UART_DATA_8_BITS,
        .parity    = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE
    };
    uart_param_config(UART_NUM_0, &uart_config);
    // esp_err_t uart_driver_install(uart_port_t uart_num, int rx_buffer_size, int tx_buffer_size, int queue_size, QueueHandle_t *uart_queue, int no_use)
    // rx_buffer need to larger than UART_FIFO_LEN, tx_buffer can be zero (send data with blocking).
    uart_driver_install(UART_NUM_0, buf_size, 0, 0, NULL, 0);
}

void app_main(){
    if(esp_efuse_mac_get_default(mac_addr) != ESP_OK){
        WARN("get MAC fail...");
    }
    setup_uart(115200, 256);
    INFO(" ");
    INFO("[APP] Startup..");
    INFO("[APP] MAC Address: %02X:%02X:%02X:%02X:%02X:%02X", mac_addr[0], mac_addr[1], mac_addr[2], mac_addr[3], mac_addr[4], mac_addr[5]);
    INFO("[APP] Free memory: %d bytes", esp_get_free_heap_size());
    INFO("[APP] IDF version: %s", esp_get_idf_version());
    
    Packet_t pack;
    Packet_t* self = &pack;
    
    DBG("mem after create a packet: %d", esp_get_free_heap_size());

    char* str = packet_to_string(self);
    DBG("before: %s", str);
    free(str);

    packet_init(self, "key1", NULL, 0);
    str = packet_to_string(self);
    DBG("key1:  %s", str);
    free(str);

    packet_init(self, "key2", "123", 3);
    str = packet_to_string(self);
    DBG("key2:  %s", str);
    free(str);

    for (int i = 999; i > 0; i--) {
        INFO("Restarting in %d seconds...\n", i);
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
    INFO("Restarting now.\n");
    fflush(stdout);
    esp_restart();
}