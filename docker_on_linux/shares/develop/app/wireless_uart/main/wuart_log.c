#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "wuart_utils.h"

const char* WUART_TAG = "wireless_uart";

static void buffer_to_hex(const void* buffer, uint16_t buff_len, char* output, size_t olen){
    memset(output, 0, olen);
    const char* buf_c = buffer;
    size_t idx = 0;
    size_t rem = olen;
    for(uint16_t i = 0; i < buff_len && rem > 0; i++){
        if(i > 0){
            if(i % 8 == 0) {
                if(rem >= 2){
                    strcat(output, "  ");
                    idx += 2;
                    rem -= 2;
                } else return;
            }
            else {
                if(rem >= 1){
                    strcat(output, " ");
                    idx += 1;
                    rem -= 1;
                } else return;
            }
        }
        if(rem >= 2){
            sprintf(output+idx, "%02x", buf_c[i]);  
            idx += 2;
            rem -= 2;
        } else return;
    }
}

static void buffer_to_char(const void* buffer, uint16_t buff_len, char* output, size_t olen){
    memset(output, 0, olen);
    const char* buf_c = buffer;
    size_t idx = 0;
    size_t rem = olen;
    for(uint16_t i = 0; i < buff_len && rem > 0; i++){
        if(is_word(buf_c[i])) output[idx] = buf_c[i];
        else output[idx] = '.';
        idx++;
        rem--;
    }
}

void esp_log_buffer_hex_internal(const char *tag, const void *buffer, uint16_t buff_len, esp_log_level_t level){
    size_t row;
    char seg[49] = {0};
    for(row = 0; row < buff_len; row += 16){
        size_t clen = row + 16 < buff_len ? 16 : buff_len - row;
        buffer_to_hex((const char*)buffer+row, clen, seg, sizeof(seg));
        esp_log_write(level, tag, "%-13p%-48s", buffer, seg);
    }
}

void esp_log_buffer_char_internal(const char *tag, const void *buffer, uint16_t buff_len, esp_log_level_t level){
    size_t row;
    char seg[17] = {0};
    for(row = 0; row < buff_len; row += 16){
        size_t clen = row + 16 < buff_len ? 16 : buff_len - row;
        buffer_to_char((const char*)buffer+row, clen, seg, sizeof(seg));
        esp_log_write(level, tag, "%-13p|%s|", buffer, seg);
    }
}

void esp_log_buffer_hexdump_internal(const char *tag, const void *buffer, uint16_t buff_len, esp_log_level_t level){
    size_t row;
    char seg1[49] = {0}, seg2[17] = {0};
    for(row = 0; row < buff_len; row += 16){
        size_t clen = row + 16 < buff_len ? 16 : buff_len - row;
        buffer_to_hex((const char*)buffer+row, clen, seg1, sizeof(seg1));
        buffer_to_char((const char*)buffer+row, clen, seg2, sizeof(seg2));
        esp_log_write(level, tag, "%-13p%-50s|%s|", buffer, seg1, seg2);
    }
}