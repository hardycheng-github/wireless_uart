#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "wuart_utils.h"

static const char* STR_NULL = "(null)";

bool set_str_auto_alloc(char** dest_p, char* src){
    if(dest_p == NULL) return false;
    if(src == NULL) src = (char*)STR_NULL;
    size_t len = strlen(src);
    if(*dest_p == src) return true;
    char* dest_new = (char*) calloc(1, len+1);
    if(dest_new == NULL) return false;
    if(*dest_p != NULL) free(*dest_p);
    strcpy(dest_new, src);
    *dest_p = dest_new;
    return true;
}

bool set_list_auto_alloc(size_t tsize, void** dest_p, void* src, size_t num){
    if(dest_p == NULL) return false;
    DBG("[before] tsize %u, dest %p, src %p, num %u", tsize, *dest_p, src, num);
    if(src == NULL || num == 0){
        DBG("1");
        if(*dest_p != NULL) free(*dest_p);
        *dest_p = NULL;
        return true;
    }
    DBG("2");
    void* dest_new = (char*) calloc(tsize, num);
    if(dest_new == NULL) return false;
    if(*dest_p != NULL) free(*dest_p);
    memcpy(dest_new, src, tsize*num);
    *dest_p = dest_new;
    DBG("3");
    DBG("[after] tsize %u, dest %p, src %p, num %u", tsize, *dest_p, src, num);
    return true;
}

bool set_bytes_auto_alloc(char** dest_p, char* src, size_t num){
    return set_list_auto_alloc(1, (void**)dest_p, (void*)src, num);
}

bool set_str_on_preallocated(char* dest, size_t limit, char* src){
    if(dest == NULL) return false;
    if(src == NULL) src = (char*)STR_NULL;
    size_t len = strlen(src);
    size_t max = len > limit-1 ? limit-1 : len;
    strncpy(dest, src, max);
    dest[max] = '\0';
    return true;
}

bool set_list_on_preallocated(size_t tsize, void* dest, size_t limit, void* src, size_t num){
    if(dest == NULL) return false;
    if(src == NULL || num == 0) return true;
    size_t max = tsize*num > limit ? limit : tsize*num;
    size_t real_num = (max / tsize);
    if(real_num == 0) return false;
    memcpy(dest, src, tsize*real_num);
    return true;
}

bool set_bytes_on_preallocated(char* dest, size_t limit, char* src, size_t num){
    return set_list_on_preallocated(1, (void*)dest, limit, (void*)src, num);
}

char calc_xor_checksum(char* data, size_t len){
    char checksum = 0;
    if(len > 0)
        for(int i = 0; i < len; i++)
            checksum = checksum ^ data[i];
    return checksum;
}

/**
 * encode rules:
 * - words: from space(0x20) to '~'(0x7E)
 * - if not word: bytes to '\x00'-'\xFF', ex: \n(0x0d) -> '\x0d'
 * - if backslash: append twice, ex: backslash(0x5c) -> '\\'
 */
bool is_word(char c){
    return 0x20 <= c && c <= 0x7E;
}

size_t bytes_encode(char* in, size_t ilen, char* out, size_t olen){
    if(in == NULL || out == NULL) return 0;
    size_t oidx = 0;
    size_t orem = olen - oidx;
    for(int i = 0; i < ilen; i++){
        char r = in[i];
        if(!is_word(r)){
            //r is not word
            if(orem >= 4){
                //format \xHH
                sprintf(out+oidx, "\\x%02x", r);
                oidx += 4;
                orem -= 4;
            } else return 0;
        } else if(r == 0x5c){
            // r is '\'
            if(orem >= 2){
                //append '\' twice
                out[oidx++] = 0x5c;
                out[oidx++] = 0x5c;
                orem -= 2;
            } else return 0;
        } else {
            if(orem >= 1){
                out[oidx++] = r;
                orem--;
            } else return 0;
        }
    }
    return oidx;
}

size_t bytes_decode(char* in, size_t ilen, char* out, size_t olen){
    if(in == NULL || out == NULL) return 0;
    size_t oidx = 0;
    size_t orem = olen - oidx;
    // states
    // 0: normal
    // 1: backslash appear
    // 2: backslash + hex
    // 3: hex num 1
    int state = 0;
    char hex_1 = 0;
    for(int i = 0; i < ilen; i++){
        char r = in[i];
        if(state == 1){
            // if '\' appear twice, is symbol '\'
            if(r == 0x5c){
                if(orem >= 1){
                    out[oidx++] = r;
                    orem--;
                    state = 0;
                } else return 0;
            } else if(r == 0x58 || r == 0x78){
                // 0x58 -> X, 0x78 -> x
                state = 2;
            } else {
                // unknown situation, write backslash and this byte into raw.
                WARN("decode fail: '\\' + '%02x'", r);
                if(orem >= 2){
                    out[oidx++] = '\\';
                    out[oidx++] = r;
                    orem -= 2;
                    state = 0;
                } else return 0;
            }
        } else if(state == 2){
            // r in 0-9, a-h, A-H
            if((0x30 <= r && r <= 0x39) || (0x61 <= r && r <= 0x68) || (0x41 <= r && r <= 0x48)){
                hex_1 = r;
                state = 3;
            } else {
                // unknown situation, write '\x' and this byte into raw.
                WARN("decode fail: \\x%02x", r);
                if(orem >= 3){
                    out[oidx++] = '\\';
                    out[oidx++] = 'x';
                    out[oidx++] = r;
                    orem -= 3;
                    state = 0;
                } else return 0;
            }
        } else if(state == 3){
            // r in 0-9, a-h, A-H
            if((0x30 <= r && r <= 0x39) || (0x61 <= r && r <= 0x68) || (0x41 <= r && r <= 0x48)){
                char hex_byte;
                int hex_int;
                char tmp_hex_str[3];
                tmp_hex_str[0] = hex_1;
                tmp_hex_str[1] = r;
                tmp_hex_str[2] = '\0';
                sscanf(tmp_hex_str, "%x", &hex_int);
                hex_byte = (char) hex_int;
                DBG("decoded: \\x%02x", hex_byte);
                if(orem >= 1){
                    out[oidx++] = hex_byte;
                    orem--;
                    state = 0;
                } else return 0;
            } else {
                // unknown situation, write '\x' + hex_1 and this byte into raw.
                WARN("decode fail: '\\x' + '%02x' + '%02x'", hex_1, r);
                if(orem >= 4){
                    out[oidx++] = '\\';
                    out[oidx++] = 'x';
                    out[oidx++] = hex_1;
                    out[oidx++] = r;
                    orem -= 4;
                    state = 0;
                } else return 0;
            }
        } else{
            if(r == '\\'){
                state = 1;
            } else {
                if(orem >= 1){
                    out[oidx++] = r;
                    orem--;
                    state = 0;
                } else return 0;
            }
        }
    }
    return oidx;
}