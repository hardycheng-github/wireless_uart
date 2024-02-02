import argparse
import socket
import struct
import logging
import serial
import select
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
formatter = logging.Formatter('[%(asctime)s] %(levelname)-7s| %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

app_version = '0.5'
server_host = '127.0.0.1'
server_port = 58266
socket_buffer_size = 4096
recv_timeout_sec = 0.01
debug_enable = False
data_encode = False

uart_local_path = '/dev/ttyUSB0'
uart_local_baud = 115200
uart_remote_path = 'COM826'
uart_remote_baud = 115200

"""
Packet Structure
Start Symbol - uint16 - 0x23 0x24
Data Length - uint32 - 4 bytes - only for data bytes, not include checksum
Data Bytes - bytearray - [Packet Length] bytes
 > Key String - string - dynamic bytes (1~kN) - until '=', if '=' not exist, whole bytes as key string, and value as empty
 > Value Bytes - bytearray - dynamic bytes (0~vN) - until end (allow empty)
XOR Checksum - 1 byte
End Symbol - uint16 - 0x24 0x23 (Optional)
"""
class Packet:
    SYMBOL_START = 0x2423
    SYMBOL_END = 0x2324
    SYMBOL_START_BYTES = b'\x23\x24'
    SYMBOL_END_BYTES = b'\x24\x23'
    PACKET_MIN = (2+4+1+1) # start + length + min data + checksum

    def __init__(self, key_str:str, val_bytes:bytearray=bytearray()):
       self.key_str = ''
       self.val_bytes = bytearray()
       self.data_bytes = bytearray()
       self.data_size = 0
       self.checksum = 0
       self.set_key_value(key_str, val_bytes)
    
    def __str__(self):
        if self.val_bytes == None or len(self.val_bytes) == 0:
            return "key=%s,val=None" % (self.key_str)
        else:
            return "key=%s,val=0x%s" % (self.key_str, self.val_bytes.hex())
    
    def set_key_value(self, key_str:str, val_bytes:bytearray):
        self.key_str = key_str
        self.val_bytes = val_bytes
        if len(val_bytes) > 0:
            self.data_bytes = key_str.encode() + b'=' + val_bytes
            self.data_size = len(self.data_bytes)
        else:
            self.data_bytes = key_str.encode()
            self.data_size = len(self.data_bytes)
        self.checksum = Packet.calc_checksum(self.data_bytes)
    
    def do_encode(self):
        if self.val_bytes == None or len(self.val_bytes) == 0:
            return
        logger.debug("=== do_encode ===")
        logger.debug("0x" + self.val_bytes.hex())
        self.set_key_value(self.key_str, Packet.bytes_encode(self.val_bytes))
        logger.debug("0x" + self.val_bytes.hex())
        logger.debug("=================")
    
    def do_decode(self):
        if self.val_bytes == None or len(self.val_bytes) == 0:
            return
        logger.debug("=== do_decode ===")
        logger.debug("0x" + self.val_bytes.hex())
        self.set_key_value(self.key_str, Packet.bytes_decode(self.val_bytes))
        logger.debug("0x" + self.val_bytes.hex())
        logger.debug("=================")

    def get_bytes(self):
        raw_bytes = struct.pack('<1H1I', self.SYMBOL_START, self.data_size)
        raw_bytes += self.data_bytes
        raw_bytes += self.checksum.to_bytes(1, 'little')
        raw_bytes += Packet.SYMBOL_END_BYTES
        return raw_bytes
    
    @staticmethod
    def calc_checksum(raw: bytearray):
        checksum = 0
        for b in raw:
            checksum = checksum ^ b & 0xFF
        return checksum
    
    """
    encode rules:
    - words: from space(0x20) to '~'(0x7E)
    - if not word: bytes to '\x00'-'\xFF', ex: \n(0x0d) -> '\x0d'
    - if backslash: append twice, ex: backslash(0x5c) -> '\\'
    """
    @staticmethod
    def is_word(char: int):
        # start ' ', until '~', not include 0x7F(DEL)
        return char in range(0x20, 0x7F) 
    
    @staticmethod
    def bytes_encode(raw_bytes:bytearray):
        new_raw = bytearray()
        for r in raw_bytes:
            # r is not word
            if not Packet.is_word(r):
                new_raw += b"\\x%02x" % r
            # r is '\'
            elif r == 0x5c:
                # append '\' twice
                new_raw += b"\\\\"
            else:
                new_raw += r.to_bytes(1, 'little')
        return new_raw

    @staticmethod
    def bytes_decode(raw_bytes:bytearray):
        new_raw = bytearray()
        # states
        # 0: normal
        # 1: backslash appear
        # 2: backslash + hex
        # 3: hex num 1
        state = 0
        hex_1 = 0
        for r in raw_bytes:
            if state == 1:
                # if '\' appear twice, is symbol '\'
                if r == 0x5c:
                    new_raw += r.to_bytes(1, 'little')
                    state = 0
                elif r == 0x58 or r == 0x78:
                    # 0x58 -> X, 0x78 -> x
                    state = 2
                else:
                    # unknown situation, write backslash and this byte into raw.
                    logger.warn("decode fail: '\\' + '%02x'" % r)
                    new_raw += b'\\'
                    new_raw += r.to_bytes(1, 'little')
                    state = 0
            elif state == 2:
                # r in 0-9, a-h, A-H
                if r in range(0x30, 0x40) or r in range(0x61, 0x69) or r in range(0x41, 0x49):
                    hex_1 = r
                    state = 3
                else:
                    # unknown situation, write '\x' and this byte into raw.
                    logger.warn("decode fail: '\\x' + '%02x'" % r)
                    new_raw += b'\\x'
                    new_raw += r.to_bytes(1, 'little')
                    state = 0
            elif state == 3:
                # r in 0-9, a-h, A-H
                if r in range(0x30, 0x40) or r in range(0x61, 0x69) or r in range(0x41, 0x49):
                    hex_bytes = bytes.fromhex("%c%c" % (hex_1, r))[:1]
                    logger.debug('decoded: \\x' + hex_bytes.hex())
                    new_raw += hex_bytes
                    state = 0
                else:
                    # unknown situation, write '\x' + hex_1 and this byte into raw.
                    logger.warn("decode fail: '\\x' + '%02x' + '%02x'" % (hex_1, r))
                    new_raw += b'\\x'
                    new_raw += hex_1.to_bytes(1, 'little')
                    new_raw += r.to_bytes(1, 'little')
                    state = 0
            else:
                if r == 0x5c:
                    # 0x5c -> '\'
                    state = 1
                else:
                    new_raw += r.to_bytes(1, 'little')
                    state = 0
        return new_raw

    @staticmethod
    def parse(raw_bytes:bytearray):
        try:
            while raw_bytes is not None and len(raw_bytes) >= Packet.PACKET_MIN:
                start_idx = raw_bytes.find(Packet.SYMBOL_START_BYTES)
                if start_idx == 0:
                    logger.debug("raw=0x" + raw_bytes.hex())
                    _, data_size = struct.unpack('<1H1I', raw_bytes[:6])
                    if len(raw_bytes) < 6+1+data_size:
                        logger.debug('packet size not enough.')
                        return None
                    data_bytes = raw_bytes[6:6+data_size]
                    checksum = raw_bytes[6+data_size]
                    checktmp = Packet.calc_checksum(data_bytes)
                    if checktmp == checksum:
                        logger.debug("Packet Found!")
                        split_idx = data_bytes.find(b'=')
                        if split_idx > 0:
                            key_str = data_bytes[:split_idx].decode()
                            val_bytes = data_bytes[split_idx+1:]
                        else:
                            key_str = data_bytes.decode()
                            val_bytes = bytearray()
                        new_packet = Packet(key_str, val_bytes)
                        logger.debug(str(new_packet))
                        return new_packet
                    raw_bytes = raw_bytes[2:]
                elif start_idx > 0:
                    raw_bytes = raw_bytes[start_idx:]
                else:
                    return None
        except Exception as ex2:
            logger.error("[!] Packet parse err: %s" % str(ex2))
        return None
    

class WirelessUartConnectHelper(socket.socket):
    def __init__(self, host, port):
        global uart_local_path, uart_local_baud, uart_remote_path, uart_remote_baud, socket_buffer_size, recv_timeout_sec, data_encode
        super().__init__(socket.AF_INET, socket.SOCK_STREAM)
        self.host = host
        self.port = port
        self.is_running = False
        self.recv_buffer = bytearray()
        self.buf_size = socket_buffer_size
        self.recv_timeout = recv_timeout_sec
        self.uart_dev = None
        self.uart_path = uart_local_path
        self.uart_baud = uart_local_baud
        self.remote_path = uart_remote_path
        self.remote_baud = uart_remote_baud
        self.data_encode = data_encode
    
    def start_forever(self):
        while True:
            try:
                self.uart_open()
                logger.info('start connect to server(%s, %d)' % (self.host, self.port))
                self.connect((self.host, self.port))
                logger.info('+++ server(%s, %d) connected +++' % (self.host, self.port))
                self.is_running = True
                self.handle()
            except Exception as ex1:
                logger.debug('connect err: ' + str(ex1))
            self.is_running = False
            logger.info('--- server(%s, %d) disconnected ---' % (self.host, self.port))
            time.sleep(10)
            logger.info('try to reconnect...')

    def error(self, msg):
        logger.error('[!] server(%s, %d) err: %s' % (self.host, self.port, str(msg)))
        self.send_packet('error', str(msg))

    def uart_open(self):
        try:
            if isinstance(self.uart_dev, serial.Serial):
                if self.uart_dev.portstr == self.uart_path and self.uart_dev.baudrate == self.uart_baud:
                    logger.debug('device(%s, %d) already opened.' % (self.uart_path, self.uart_baud))
                    return True
                logger.warn("last device(%s) still using, try to close." % self.uart_dev.portstr)
                self.uart_close()
            self.uart_dev = serial.Serial(self.uart_path, self.uart_baud)
            if self.uart_dev != None and self.uart_dev.is_open:
                logger.info('+++ uart(%s,%d) open ok +++' % (self.uart_path, self.uart_baud))
                return True
        except Exception as ex1:
            logger.error('uart open fail: ' + str(ex1))
        return False

    def uart_close(self):
        try:
            if isinstance(self.uart_dev, serial.Serial):
                try:
                    portstr = self.uart_dev.portstr
                    self.uart_dev.close()
                    self.uart_dev = None
                    logger.info('--- uart(%s) close ok ---' % portstr)
                    return True
                except:
                    logger.warn("device(%s) close fail..." % self.uart_dev.portstr)
        except Exception as ex1:
            logger.error('uart close fail: ' + str(ex1))
        return False
    
    def handle_packet(self, new_packet: Packet):
        if not isinstance(new_packet, Packet):
            return
        elif new_packet.key_str == 'data':
            if not self.is_running:
                self.error('task not ready.')
            elif new_packet.data_size <= 0:
                self.error('recv empty data.')
            else:
                self.uart_dev.write(new_packet.val_bytes)
                self.uart_dev.flush()
        elif new_packet.key_str == 'error':
            logger.error('[!] server(%s, %d) recv err: %s' % (self.host, self.port, new_packet.val_bytes.decode()))
        else:
            self.error('unknown keyword: ' + new_packet.key_str)

    def send_packet(self, key_str:str, val = bytearray()):
        try:
            if val is None:
                self.send_packet(key_str)
            elif isinstance(val, int):
                self.send_packet(key_str, str(val).encode())
            elif isinstance(val, str):
                self.send_packet(key_str, val.encode())
            else:
                val_bytes = bytes(val)
                # # if end with \r, append \n
                # if len(val_bytes) > 0 and val_bytes[-1] == 0x0d:
                #     val_bytes += b'\n'
                pack = Packet(key_str, val_bytes)
                if self.data_encode:
                    pack.do_encode()
                raw_bytes = pack.get_bytes()
                logger.debug("Packet Send!")
                logger.debug(str(pack))
                logger.debug("raw=0x" + raw_bytes.hex())
                self.sendall(raw_bytes)
        except Exception as ex1:
            logger.error('send packet err: ' + str(ex1))

    def handle(self):
        self.send_packet('path', self.remote_path)
        self.send_packet('baud', self.remote_baud)
        self.send_packet('start')
        try:
            while self:
                ready = select.select([self], [], [], self.recv_timeout)
                if ready[0]:
                    recv_raw = self.recv(self.buf_size).strip()
                    if recv_raw is not None and len(recv_raw) > 0:
                        self.recv_buffer += recv_raw
                        while self.recv_buffer.find(Packet.SYMBOL_START_BYTES) >= 0:
                            new_packet = Packet.parse(self.recv_buffer)
                            if new_packet is not None:
                                if self.data_encode:
                                    new_packet.do_decode()
                                self.recv_buffer = self.recv_buffer[2+4+1+new_packet.data_size:]
                                self.handle_packet(new_packet)
                            else:
                                break
                        # make sure that start symbol not exists and last byte do not possentially being a start symbol
                        if len(self.recv_buffer) > 0 and \
                            self.recv_buffer.find(Packet.SYMBOL_START_BYTES) < 0 and \
                            self.recv_buffer[-1] != (Packet.PACKET_MIN & 0xFF):
                            self.recv_buffer = bytearray()
                if isinstance(self.uart_dev, serial.Serial) and self.uart_dev.in_waiting > 0:
                    rx_bytes = self.uart_dev.read_all() # always read to avoid too many data hanged
                    if self.is_running and rx_bytes != None and len(rx_bytes) > 0:
                        self.send_packet('data', rx_bytes)
        except Exception as ex1:
            logger.error("server(%s, %d) err: %s" % (self.host, self.port, str(ex1)))
        logger.info('--- server(%s, %d) exit ---' % (self.host, self.port))


if __name__ == "__main__":
    logger.info("=============================%s" % ("=" * len(app_version)))
    logger.info("= Wireless UART Server ver.%s =" % app_version)
    logger.info("=============================%s" % ("=" * len(app_version)))
    try:
        parser = argparse.ArgumentParser(description="Wireless UART Server ver.%s" % app_version)
        parser.add_argument(
            "-i",
            "--host",
            default=server_host,
            type=str,
            help='Set Server Host Name or Ip Address (Default %s)' % server_host)
        parser.add_argument(
            "-p",
            "--port",
            default=server_port,
            type=int,
            help='Set Server Port Number (Default %d)' % server_port)
        parser.add_argument(
            "-ulp",
            "--uart_local_path",
            default=uart_local_path,
            type=str,
            help='Set UART Local Path (Default %s)' % uart_local_path)
        parser.add_argument(
            "-ulb",
            "--uart_local_baud",
            default=uart_local_baud,
            type=int,
            help='Set UART Local Baudrate (Default %d)' % uart_local_baud)
        parser.add_argument(
            "-urp",
            "--uart_remote_path",
            default=uart_remote_path,
            type=str,
            help='Set UART Remote Path (Default %s)' % uart_remote_path)
        parser.add_argument(
            "-urb",
            "--uart_remote_baud",
            default=uart_remote_baud,
            type=int,
            help='Set UART Remote Baudrate (Default %d)' % uart_remote_baud)
        parser.add_argument(
            "-d",
            "--debug",
            default=debug_enable,
            action='store_true',
            help='Set Debug Logger Enable (Default Disable)')
        parser.add_argument(
            "-e",
            "--encode",
            default=data_encode,
            action='store_true',
            help='Set Data Encode Enable (Default Disable)')
        parser.add_argument(
            "-b",
            "--buffer_size",
            default=socket_buffer_size,
            type=int,
            help='Set Socket Receive Buffer Size (Default %dKB)' % (socket_buffer_size / 1024))
        parser.add_argument(
            "-t",
            "--recv_timeout",
            default=recv_timeout_sec,
            type=float,
            help='Set Socket Receive Timeout Seconds (Default %.1f)' % recv_timeout_sec)

        args = parser.parse_args()

        server_host = args.host
        server_port = args.port
        uart_local_path = args.uart_local_path
        uart_local_baud = args.uart_local_baud
        uart_remote_path = args.uart_remote_path
        uart_remote_baud = args.uart_remote_baud
        socket_buffer_size = args.buffer_size
        recv_timeout_sec = args.recv_timeout
        debug_enable = args.debug
        data_encode = args.encode
        if debug_enable:
            logger.setLevel(logging.DEBUG)
            logger.warning('[!] Debug Mode Enable')
        logger.debug("[!] config: host %s, port %d, buffer %d, timeout %.1f, debug %s" % (
        server_host, server_port, socket_buffer_size, recv_timeout_sec, str(debug_enable)))

        helper = WirelessUartConnectHelper(server_host, server_port)
        helper.start_forever()
    except Exception as ex1:
        logger.error("[!] server running err: %s" % str(ex1))
        input("\n[!] Press key to exit...")
    logger.debug("--- on stop ---")
