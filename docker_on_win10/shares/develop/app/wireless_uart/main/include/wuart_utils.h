#include "wuart_packet.h"
#include "wuart_log.h"

bool set_str_auto_alloc(char** dest_p, char* src);

bool set_list_auto_alloc(size_t tsize, void** dest_p, void* src, size_t num);

bool set_bytes_auto_alloc(char** dest_p, char* src, size_t num);

bool set_str_on_preallocated(char* dest, size_t limit, char* src);

bool set_list_on_preallocated(size_t tsize, void* dest, size_t limit, void* src, size_t num);

bool set_bytes_on_preallocated(char* dest, size_t limit, char* src, size_t num);

char calc_xor_checksum(char* data, size_t len);

/**
 * encode rules:
 * - words: from space(0x20) to '~'(0x7E)
 * - if not word: bytes to '\x00'-'\xFF', ex: \n(0x0d) -> '\x0d'
 * - if backslash: append twice, ex: backslash(0x5c) -> '\\'
 */
bool is_word(char c);

size_t bytes_encode(char* in, size_t ilen, char* out, size_t olen);

size_t bytes_decode(char* in, size_t ilen, char* out, size_t olen);