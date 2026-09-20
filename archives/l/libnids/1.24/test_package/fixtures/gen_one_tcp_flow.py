#!/usr/bin/env python3
"""Generate one_tcp_flow.pcap — deterministic offline fixture for libnids test_package.

Constructs a classic TCP session between 10.0.0.1:44000 (client) and
10.0.0.2:80 (server) over Ethernet (DLT_EN10MB), with correct IPv4 header
checksums and TCP checksums (libnids drops bad-checksum segments by default):

  1. SYN        client->server seq=1000
  2. SYN+ACK    server->client seq=5000 ack=1001
  3. ACK        client->server ack=5001
  4. PSH+ACK    client->server seq=1001 "GET / HTTP/1.0\r\n\r\n" (18 bytes)
  5. PSH+ACK    server->client seq=5001 "HELLO-LIBNIDS" (13 bytes)
  6. FIN+ACK    client->server seq=1019 ack=5014
  7. FIN+ACK    server->client seq=5014 ack=1020
  8. ACK        client->server ack=5015  -> both FIN_CONFIRMED -> NIDS_CLOSE

Expected libnids callback trace: JUST_EST, DATA(client), DATA(server), CLOSE.
"""

import struct
import sys

CLIENT_IP = "10.0.0.1"
SERVER_IP = "10.0.0.2"
CLIENT_PORT = 44000
SERVER_PORT = 80

TH_FIN = 0x01
TH_SYN = 0x02
TH_RST = 0x04
TH_PSH = 0x08
TH_ACK = 0x10


def ip_checksum(data):
    if len(data) % 2:
        data += b"\x00"
    s = 0
    for i in range(0, len(data), 2):
        s += (data[i] << 8) + data[i + 1]
    while s >> 16:
        s = (s & 0xFFFF) + (s >> 16)
    return (~s) & 0xFFFF


def ip_to_bytes(ip):
    return bytes(int(x) for x in ip.split("."))


def make_tcp(src_ip, dst_ip, sport, dport, seq, ack, flags, payload=b"", window=65535):
    # TCP header (20 bytes), checksum computed over IPv4 pseudo-header
    offset_flags = (5 << 12) | flags
    tcp_no_sum = struct.pack(
        "!HHIIHHHH",
        sport, dport, seq, ack, offset_flags, window, 0, 0,
    )
    pseudo = ip_to_bytes(src_ip) + ip_to_bytes(dst_ip) + struct.pack(
        "!BBH", 0, 6, len(tcp_no_sum) + len(payload)
    )
    csum = ip_checksum(pseudo + tcp_no_sum + payload)
    tcp = struct.pack(
        "!HHIIHHHH", sport, dport, seq, ack, offset_flags, window, csum, 0
    )
    return tcp + payload


def make_ip(src_ip, dst_ip, protocol, payload):
    total_len = 20 + len(payload)
    ip_no_sum = struct.pack(
        "!BBHHHBBH4s4s",
        0x45, 0, total_len, 0x1234, 0x4000, 64, protocol, 0,
        ip_to_bytes(src_ip), ip_to_bytes(dst_ip),
    )
    csum = ip_checksum(ip_no_sum)
    return struct.pack(
        "!BBHHHBBH4s4s",
        0x45, 0, total_len, 0x1234, 0x4000, 64, protocol, csum,
        ip_to_bytes(src_ip), ip_to_bytes(dst_ip),
    )


def make_packet(src_mac, dst_mac, src_ip, dst_ip, sport, dport,
                seq, ack, flags, payload=b""):
    eth = bytes.fromhex(src_mac.replace(":", "")) + bytes.fromhex(
        dst_mac.replace(":", "")
    ) + struct.pack("!H", 0x0800)
    tcp = make_tcp(src_ip, dst_ip, sport, dport, seq, ack, flags, payload)
    ip = make_ip(src_ip, dst_ip, 6, tcp)
    return eth + ip + tcp


def main():
    c = CLIENT_IP
    s = SERVER_IP
    client_mac = "02:00:00:00:00:01"
    server_mac = "02:00:00:00:00:02"

    pkts = [
        # 3-way handshake
        make_packet(client_mac, server_mac, c, s, CLIENT_PORT, SERVER_PORT,
                    1000, 0, TH_SYN),
        make_packet(server_mac, client_mac, s, c, SERVER_PORT, CLIENT_PORT,
                    5000, 1001, TH_SYN | TH_ACK),
        make_packet(client_mac, server_mac, c, s, CLIENT_PORT, SERVER_PORT,
                    1001, 5001, TH_ACK),
        # data client -> server
        make_packet(client_mac, server_mac, c, s, CLIENT_PORT, SERVER_PORT,
                    1001, 5001, TH_PSH | TH_ACK, b"GET / HTTP/1.0\r\n\r\n"),
        # data server -> client
        make_packet(server_mac, client_mac, s, c, SERVER_PORT, CLIENT_PORT,
                    5001, 1019, TH_PSH | TH_ACK, b"HELLO-LIBNIDS"),
        # close: FIN client, FIN server, final ACK
        make_packet(client_mac, server_mac, c, s, CLIENT_PORT, SERVER_PORT,
                    1019, 5014, TH_FIN | TH_ACK),
        make_packet(server_mac, client_mac, s, c, SERVER_PORT, CLIENT_PORT,
                    5014, 1020, TH_FIN | TH_ACK),
        make_packet(client_mac, server_mac, c, s, CLIENT_PORT, SERVER_PORT,
                    1020, 5015, TH_ACK),
    ]

    out = sys.argv[1] if len(sys.argv) > 1 else "one_tcp_flow.pcap"
    with open(out, "wb") as f:
        # pcap file header: little-endian, libpcap 2.4, DLT_EN10MB (1)
        f.write(struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
        ts_sec, ts_usec = 1735689600, 0
        for i, p in enumerate(pkts):
            f.write(struct.pack("<IIII", ts_sec, ts_usec + i, len(p), len(p)))
            f.write(p)
    print("wrote %s (%d packets)" % (out, len(pkts)))


if __name__ == "__main__":
    main()
