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

app_version = '0.3'
server_host = '127.0.0.1'
server_port = 58266
socket_buffer_size = 4096
recv_timeout_sec = 0.01
debug_enable = False

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
        global uart_local_path, uart_local_baud, uart_remote_path, uart_remote_baud, socket_buffer_size, recv_timeout_sec
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
            self.recv_buffer = bytearray()
        elif new_packet.key_str == 'data':
            if not self.is_running:
                self.error('task not ready.')
            elif new_packet.data_size <= 0:
                self.error('recv empty data.')
            else:
                self.uart_dev.write(new_packet.val_bytes)
                self.uart_dev.flush()
        elif new_packet.key_str == 'error':
            logger.error('[!] server(%s, %d) recv err: %s' % (self.host, self.port, new_packet.data_bytes.decode()))
        else:
            self.error('unknown keyword: ' + new_packet.key_str)

    def send_packet(self, key_str:str, val = None):
        try:
            if val is None:
                val_bytes = bytearray()
            elif isinstance(val, int):
                val_bytes = str(val).encode()
            elif isinstance(val, str):
                val_bytes = val.encode()
            else:
                val_bytes = bytes(val)
            pack = Packet(key_str, val_bytes)
            logger.debug("Packet Send!")
            logger.debug(str(pack))
            self.sendall(pack.get_bytes())
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
                    self.recv_buffer += self.recv(self.buf_size).strip()
                    new_packet = Packet.parse(self.recv_buffer)
                    if new_packet is not None:
                        self.handle_packet(new_packet)
                if self.uart_dev.in_waiting > 0:
                    rx_bytes = self.uart_dev.read_all() # always read to avoid too many data hanged
                    if self.is_running and rx_bytes != None and len(rx_bytes) > 0:
                        self.request.sendall(Packet('data', rx_bytes).get_bytes())
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
