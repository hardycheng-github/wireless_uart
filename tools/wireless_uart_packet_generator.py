import argparse
import struct
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
formatter = logging.Formatter('[%(asctime)s] %(levelname)-7s| %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

app_version = '0.1'

"""
Packet Structure
Start Symbol - uint16 - 0x23 0x24
Data Length - uint32 - 4 bytes - only for data bytes, not include checksum
Data Bytes - bytearray - [Packet Length] bytes
 > Key String - string - dynamic bytes (1~kN) - until '=', if '=' not exist, whole bytes as key string, and value as empty
 > Value Bytes - bytearray - dynamic bytes (0~vN) - until end (allow empty)
XOR Checksum - 1 byte
"""
class Packet:
    SYMBOL_START = 0x2423
    PACKET_MIN = (2+4+2+1) # start + length + min data + checksum

    def __init__(self, key_str:str, val_bytes:bytearray=bytearray()):
       self.key_str = ''
       self.val_bytes = bytearray()
       self.data_bytes = bytearray()
       self.data_size = 0
       self.checksum = 0
       self.set_key_value(key_str, val_bytes)
    
    def __str__(self):
        return "0x"+self.get_bytes().hex()
    
    def set_key_value(self, key_str:str, val_bytes:bytearray):
        self.key_str = key_str
        self.val_bytes = val_bytes
        if len(val_bytes) > 0:
            self.data_bytes = key_str.encode() + b'=' + val_bytes
            self.data_size = len(self.data_bytes)
        else:
            self.data_bytes = key_str.encode()
            self.data_size = len(self.data_bytes)
        self.checksum = 0
        for b in self.data_bytes:
            self.checksum = self.checksum ^ b & 0xFF

    def get_bytes(self):
        raw_bytes = struct.pack('<1H1I', self.SYMBOL_START, self.data_size)
        raw_bytes += self.data_bytes
        raw_bytes += self.checksum.to_bytes(1, 'little')
        return raw_bytes

    @staticmethod
    def parse(raw_bytes:bytearray):
        try:
            start_bytes = struct.pack('<1H', Packet.SYMBOL_START)
            while raw_bytes is not None and len(raw_bytes) >= Packet.PACKET_MIN:
                start_idx = raw_bytes.find(start_bytes)
                if start_idx == 0:
                    _, data_size = struct.unpack('<1H1I', raw_bytes[:6])
                    data_bytes = raw_bytes[6:6+data_size]
                    checksum = raw_bytes[6+data_size]
                    checktmp = 0
                    for b in data_bytes:
                        checktmp = checktmp ^ b
                    if checktmp == checksum:
                        logger.debug("Packet Found!")
                        split_idx = data_bytes.find(b'=')
                        if split_idx > 0:
                            key_str = str(data_bytes[:split_idx])
                            val_bytes = data_bytes[split_idx+1:]
                            logger.debug("key=%s,val=0x%s" % (key_str, val_bytes.hex()))
                        else:
                            key_str = str(data_bytes)
                            val_bytes = bytearray()
                            logger.debug("key=%s,val=None" % (key_str))
                        new_packet = Packet(key_str, val_bytes)
                        return new_packet
                    raw_bytes = raw_bytes[2:]
                elif start_idx > 0:
                    raw_bytes = raw_bytes[start_idx:]
                else:
                    return None
        except Exception as ex2:
            logger.error("[!] Packet parse err: %s" % str(ex2))
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TheNewDiag Egame Server ver.%s" % app_version)
    parser.add_argument(
        "-k",
        "--key",
        default='test',
        type=str,
        help='Set Keyword')
    parser.add_argument(
        "-v",
        "--val",
        default='',
        type=str,
        help='Set Value')
    parser.add_argument(
        "-d",
        "--debug",
        default=False,
        action='store_true',
        help='Set Debug Logger Enable (Default Disable)')
    args = parser.parse_args()
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.warning('[!] Debug Mode Enable')
    if len(args.val) == 0:
        raw = Packet(args.key).get_bytes()
    elif args.val.startswith('0x'):
        raw = Packet(args.key, bytes.fromhex(args.val[2:])).get_bytes()
    else:
        raw = Packet(args.key, args.val.encode()).get_bytes()
    out = ''
    for r in raw:
        out += '\%02X' % r
    print(out)
    
