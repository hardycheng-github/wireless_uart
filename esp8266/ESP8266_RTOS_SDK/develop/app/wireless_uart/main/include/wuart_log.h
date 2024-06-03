#include "esp_log.h"

#undef LOG_LOCAL_LEVEL
#define LOG_LOCAL_LEVEL 5

extern const char* WUART_TAG;
#define DBG(fmt, ...) ESP_LOGD(WUART_TAG, "%s(): " fmt,__FUNCTION__, ##__VA_ARGS__)
#define ERR(fmt, ...) ESP_LOGE(WUART_TAG, "[X] %s(): " fmt,__FUNCTION__, ##__VA_ARGS__)
#define WARN(fmt, ...) ESP_LOGW(WUART_TAG, "[!] %s(): " fmt,__FUNCTION__, ##__VA_ARGS__)
#define INFO(fmt, ...) ESP_LOGI(WUART_TAG, fmt, ##__VA_ARGS__)

#undef esp_log_buffer_hex_internal
#undef esp_log_buffer_char_internal
#undef esp_log_buffer_hexdump_internal

void esp_log_buffer_hex_internal(const char *tag, const void *buffer, uint16_t buff_len, esp_log_level_t level);
void esp_log_buffer_char_internal(const char *tag, const void *buffer, uint16_t buff_len, esp_log_level_t level);
void esp_log_buffer_hexdump_internal( const char *tag, const void *buffer, uint16_t buff_len, esp_log_level_t log_level);