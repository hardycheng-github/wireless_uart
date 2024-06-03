#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "wuart_utils.h"

bool packet_is_valid(Packet_t* self){
    if(self == NULL) return false;
    return self->ready && self->key_str != NULL && strlen(self->key_str) > 0 && self->checksum != 0;
}

bool packet_release(Packet_t* self){
    if(self == NULL) return false;
    if(self->key_str != NULL) free(self->key_str);
    if(self->val_bytes != NULL) free(self->val_bytes);
    memset(self, 0, sizeof(Packet_t));
    return true;
}

bool packet_init(Packet_t* self, char* key_str, char* val_bytes, size_t val_len){
    if(!packet_release(self)) return false;
    self->ready = packet_set_key_value(self, key_str, val_bytes, val_len);
    return self->ready;
}

//remember to free pointer by yourself
char* packet_to_string(Packet_t* self){
    //Packet(ready=0|1,key=<key>,val=<len>)
    //key length max to 32 bytes
    char* str_p = (char*) malloc(64);
    size_t cur_len = 0;
    sprintf(str_p+cur_len, "Packet(");
    cur_len = strlen(str_p);
    if(self == NULL){
        sprintf(str_p+cur_len, "None");
        cur_len = strlen(str_p);
    } else {
        ESP_LOG_BUFFER_HEXDUMP("packet", self, sizeof(Packet_t), ESP_LOG_DEBUG);
        sprintf(str_p+cur_len, "ready=%d", self->ready);
        cur_len = strlen(str_p);
        if(packet_is_valid(self)){
            snprintf(str_p+cur_len, 32, ",key=%s", self->key_str);
            cur_len = strlen(str_p);
            snprintf(str_p+cur_len, 16, ",val=%d", self->val_size);
            cur_len = strlen(str_p);
        }
    }
    
    str_p[cur_len++] = ')';
    str_p[cur_len] = '\0';
    return str_p;
}

bool packet_set_key_value(Packet_t* self, char* key_str, char* val_bytes, size_t val_len){
    if(self == NULL || key_str == NULL || strlen(key_str) == 0) return false;
    if(!set_str_auto_alloc(&self->key_str, key_str)) return false;
    if(!set_bytes_auto_alloc(&self->val_bytes, val_bytes, val_len)) return false;
    if(packet_calc_checksum(self) == 0) return false;
    return true;
}

bool packet_do_encode(Packet_t* self){
    if(!packet_is_valid(self)) return false;
    if(self->val_size == 0) return true;
    bool ret = false;
    char* input = self->val_bytes;
    size_t ilen = self->val_size;
    //try to alloc output, with size `ilen*4` -> `ilen*2`, return false if all alloc fail.
    char* output = NULL;
    size_t olen = ilen * 4;
    output = (char*) malloc(olen);
    if(output == NULL) {
        olen = ilen * 2;
        output = (char*) malloc(olen);
        if(output == NULL) return false;
    }
    size_t rlen = bytes_encode(input, ilen, output, olen);
    if(rlen >= ilen) {
        packet_set_key_value(self, self->key_str, output, rlen);
        free(output);
        ret = true;
    }
    free(output);
    return ret;
}

bool packet_do_decode(Packet_t* self){
    if(!packet_is_valid(self)) return false;
    if(self->val_size == 0) return true;
    bool ret = false;
    char* input = self->val_bytes;
    size_t ilen = self->val_size;
    //try to alloc output.
    char* output = NULL;
    size_t olen = ilen;
    output = (char*) malloc(olen);
    if(output == NULL) return false;
    size_t rlen = bytes_decode(input, ilen, output, olen);
    if(rlen > 0) {
        packet_set_key_value(self, self->key_str, output, rlen);
        free(output);
        ret = true;
    }
    free(output);
    return ret;
}

size_t packet_get_data_bytes(Packet_t* self, char* buf, size_t buf_len){
    if(self == NULL || self->key_str == NULL || strlen(self->key_str) == 0) return 0;
    size_t key_len = strlen(self->key_str);
    size_t idx = 0;
    if(self->val_size > 0){
        if(buf_len >= key_len + 1 + self->val_size){
            sprintf(buf+idx, "%s=", self->key_str);
            idx += key_len+1;
            memcpy(buf+idx, self->val_bytes, self->val_size);
            idx += self->val_size;
        } else return 0;
    } else {
        if(buf_len >= key_len){
            memcpy(buf+idx, self->key_str, key_len);
            idx += key_len;
        } else return 0;
    }
    return idx;
}

char packet_calc_checksum(Packet_t* self){
    self->checksum = 0;
    if(self == NULL || self->key_str == NULL || strlen(self->key_str) == 0) return 0;
    size_t key_len = strlen(self->key_str);
    size_t buf_len = key_len + self->val_size + 1;
    char* buf = malloc(buf_len);
    if(buf == NULL) return 0;
    size_t real_len = packet_get_data_bytes(self, buf, buf_len);
    self->checksum = calc_xor_checksum(buf, real_len);
    free(buf);
    return self->checksum;
}

Packet_t* packet_parse(char* raw_bytes, size_t raw_len){
    return NULL;
}