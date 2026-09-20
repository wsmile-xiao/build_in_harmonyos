#!/usr/bin/env python3
"""Generate flows.pcap — multi-flow + bad-checksum fixture for libnids tests.

Two concurrent TCP flows plus one deliberately corrupted segment:

Flow A: 10.0.0.1:44000 <-> 10.0.0.2:80
  1. SYN          seq=1000
  2. SYN+ACK      seq=5000 ack=1001
  3. ACK          ack=5001
  4. PSH+ACK      seq=1001 "DROPME-BADSUM"  <-- TCP checksum deliberately wrong
  5. PSH+ACK      seq=1001 "GOOD-DATA"      <-- retransmission with valid checksum
  6. PSH+ACK (srv) seq=5001 "SVC-OK"
  7. FIN+ACK      seq=1010 ack=5007
  8. FIN+ACK (srv) seq=5007 ack=1011
  9. ACK          ack=5008                  -> flow A closes

Flow B: 10.0.0.3:44001 <-> 10.0.0.4:80 (handshake only, stays open at EOF)
 10. SYN          seq=2000
 11. SYN+ACK      seq=7000 ack=2001
 12. ACK          ack=7001

Expected libnids behaviour: 2x JUST_EST, client data contains ONLY
"GOOD-DATA" (bad-checksum segment silently dropped by libnids), server data
"SVC-OK", exactly 1 CLOSE (flow A), flow B open at EOF.
"""

import struct
import sys

TH_FIN = 0x01
TH_SYN = 0x02
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


def make_tcp(src_ip, dst_ip, sport, dport, seq, ack, flags, payload=b"",
             window=65535, corrupt_checksum=False):
    offset_flags = (5 << 12) | flags
    tcp_no_sum = struct.pack(
        "!HHIIHHHH", sport, dport, seq, ack, offset_flags, window, 0, 0)
    pseudo = ip_to_bytes(src_ip) + ip_to_bytes(dst_ip) + struct.pack(
        "!BBH", 0, 6, len(tcp_no_sum) + len(payload))
    csum = ip_checksum(pseudo + tcp_no_sum + payload)
    if corrupt_checksum:
        csum ^= 0xBEEF  # definitely-wrong checksum
    tcp = struct.pack("!HHIIHHHH", sport, dport, seq, ack, offset_flags,
                      window, csum, 0)
    return tcp + payload


def make_ip(src_ip, dst_ip, payload):
    total_len = 20 + len(payload)
    ip_no_sum = struct.pack(
        "!BBHHHBBH4s4s", 0x45, 0, total_len, 0x4321, 0x4000, 64, 6, 0,
        ip_to_bytes(src_ip), ip_to_bytes(dst_ip))
    csum = ip_checksum(ip_no_sum)
    return struct.pack(
        "!BBHHHBBH4s4s", 0x45, 0, total_len, 0x4321, 0x4000, 64, 6, csum,
        ip_to_bytes(src_ip), ip_to_bytes(dst_ip))


def make_packet(src_ip, dst_ip, sport, dport, seq, ack, flags, payload=b"",
                corrupt_checksum=False):
    eth = bytes.fromhex("020000000001") + bytes.fromhex("020000000002") \
        + struct.pack("!H", 0x0800)
    tcp = make_tcp(src_ip, dst_ip, sport, dport, seq, ack, flags, payload,
                   corrupt_checksum=corrupt_checksum)
    return eth + make_ip(src_ip, dst_ip, tcp) + tcp


def main():
    a1, a2 = "10.0.0.1", "10.0.0.2"   # flow A: client, server
    b1, b2 = "10.0.0.3", "10.0.0.4"   # flow B: client, server

    pkts = [
        # flow A handshake
        make_packet(a1, a2, 44000, 80, 1000, 0, TH_SYN),
        make_packet(a2, a1, 80, 44000, 5000, 1001, TH_SYN | TH_ACK),
        make_packet(a1, a2, 44000, 80, 1001, 5001, TH_ACK),
        # bad-checksum segment (must be silently dropped by libnids)
        make_packet(a1, a2, 44000, 80, 1001, 5001, TH_PSH | TH_ACK,
                    b"DROPME-BADSUM", corrupt_checksum=True),
        # valid retransmission
        make_packet(a1, a2, 44000, 80, 1001, 5001, TH_PSH | TH_ACK,
                    b"GOOD-DATA"),
        # server response
        make_packet(a2, a1, 80, 44000, 5001, 1010, TH_PSH | TH_ACK, b"SVC-OK"),
        # flow A close
        make_packet(a1, a2, 44000, 80, 1010, 5007, TH_FIN | TH_ACK),
        make_packet(a2, a1, 80, 44000, 5007, 1011, TH_FIN | TH_ACK),
        make_packet(a1, a2, 44000, 80, 1011, 5008, TH_ACK),
        # flow B handshake (stays open)
        make_packet(b1, b2, 44001, 80, 2000, 0, TH_SYN),
        make_packet(b2, b1, 80, 44001, 7000, 2001, TH_SYN | TH_ACK),
        make_packet(b1, b2, 44001, 80, 2001, 7001, TH_ACK),
    ]

    out = sys.argv[1] if len(sys.argv) > 1 else "flows.pcap"
    with open(out, "wb") as f:
        f.write(struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
        ts_sec, ts_usec = 1735689700, 0
        for i, p in enumerate(pkts):
            f.write(struct.pack("<IIII", ts_sec, ts_usec + i, len(p), len(p)))
            f.write(p)
    print("wrote %s (%d packets)" % (out, len(pkts)))


if __name__ == "__main__":
    main()
