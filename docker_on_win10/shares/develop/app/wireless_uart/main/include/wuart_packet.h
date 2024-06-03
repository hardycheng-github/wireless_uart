#include <stdint.h>
#include <stdbool.h>

#define PACKET_SYMBOL_START 0x2423
#define PACKET_SYMBOL_END 0x2324
#define PACKET_MIN_SIZE (2+4+1+1) //start + length + min data + checksum

/*
Packet Structure
Start Symbol - uint16 - 0x23 0x24
Data Length - uint32 - 4 bytes - only for data bytes, not include checksum
Data Bytes - bytearray - [Packet Length] bytes
 > Key String - string - dynamic bytes (1-kN) - until '=', if '=' not exist, whole bytes as key string, and value as empty
 > Value Bytes - bytearray - dynamic bytes (0-vN) - until end (allow empty)
XOR Checksum - 1 byte
End Symbol - uint16 - 0x24 0x23 (Optional)
*/
typedef struct {
    bool ready; //0: not ready, 1: already init and ready
    char* key_str;
    char* val_bytes;
    size_t val_size;
    char checksum;
} Packet_t;

bool packet_is_valid(Packet_t* self);

bool packet_release(Packet_t* self);

bool packet_init(Packet_t* self, char* key_str, char* val_bytes, size_t val_len);

//remember to free pointer by yourself
char* packet_to_string(Packet_t* self);

bool packet_set_key_value(Packet_t* self, char* key_str, char* val_bytes, size_t val_len);

bool packet_do_encode(Packet_t* self);

bool packet_do_decode(Packet_t* self);

size_t packet_get_data_bytes(Packet_t* self, char* buf, size_t buf_len);

char packet_calc_checksum(Packet_t* self);

Packet_t* packet_parse(char* raw_bytes, size_t raw_len);