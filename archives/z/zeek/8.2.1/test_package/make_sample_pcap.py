#!/usr/bin/env python3
"""test_package/make_sample_pcap.py — deterministic P1 sample capture generator.

Produces a classic-pcap capture (magic 0xa1b2c3d4, microsecond timestamps,
LINKTYPE_ETHERNET) with three fixed flows, consumed by test.sh (P1 consumer
test, cases 2-4):

  Flow A  TCP 10.0.0.1:41337 -> 10.0.0.2:80    HTTP GET /hello   (conn+http)
  Flow B  TCP 10.0.0.1:41338 -> 10.0.0.2:443   TLS ClientHello, SNI
                                             zeek.example.com    (conn+ssl)
  Flow C  UDP 10.0.0.1:5353  -> 10.0.0.2:53    DNS A query+reply for
                                             zeek.example.com    (conn+dns)

Determinism: nothing random anywhere (fixed addresses/ports/timestamps/
ClientHello "random"/DNS id), so the output sha256 is stable across runs and
machines; test.sh verifies it against the constant recorded in MANIFEST.yml.
The pcap is generated at test time (this script is the committed artifact;
no binary capture file is stored in the repo).

Standard library only. Usage: python3 make_sample_pcap.py [out.pcap]
"""
import hashlib
import os
import struct
import sys

MAGIC = 0xA1B2C3D4            # classic pcap, microsecond resolution
LINKTYPE_ETHERNET = 1
BASE_TS = 1700000000          # fixed epoch; packets step +1 ms

PROTO_TCP = 6
PROTO_UDP = 17

CLIENT_IP = "10.0.0.1"
SERVER_IP = "10.0.0.2"
CLIENT_MAC = bytes.fromhex("020000000001")
SERVER_MAC = bytes.fromhex("020000000002")

# Fixed endpoints per flow.
A_SRC_PORT, A_DST_PORT = 41337, 80     # HTTP
B_SRC_PORT, B_DST_PORT = 41338, 443    # TLS
C_SRC_PORT, C_DST_PORT = 5353, 53      # DNS

# TCP flags.
F_SYN = 0x02
F_FIN = 0x01
F_ACK = 0x10
F_PSH = 0x08


def pcap_global_header():
    # magic, version 2.4, thiszone, sigfigs, snaplen, network
    return struct.pack("<IHHiiII", MAGIC, 2, 4, 0, 0, 65535, LINKTYPE_ETHERNET)


def _ip_checksum(hdr):
    s = 0
    for i in range(0, len(hdr), 2):
        s += (hdr[i] << 8) | hdr[i + 1]
    while s >> 16:
        s = (s & 0xFFFF) + (s >> 16)
    return struct.pack("!H", (~s) & 0xFFFF)


def ipv4(src, dst, proto, payload_len, ident):
    total = 20 + payload_len
    hdr = struct.pack(
        "!BBHHHBBH4s4s", 0x45, 0, total, ident, 0x4000, 64, proto, 0,
        bytes(map(int, src.split("."))), bytes(map(int, dst.split("."))))
    return hdr[:10] + _ip_checksum(hdr[:10]) + hdr[12:]


def tcp_seg(sport, dport, seq, ack, flags, payload=b""):
    # data offset 5 (no options); checksum 0 (parsers do not verify it).
    return struct.pack("!HHIIBBHHH", sport, dport, seq, ack, 5 << 4, flags,
                       65535, 0, 0) + payload


def udp_seg(sport, dport, payload):
    # checksum 0 (valid for captures; parsers do not verify it).
    return struct.pack("!HHHH", sport, dport, 8 + len(payload), 0) + payload


def pcap_record(idx, src_ip, dst_ip, proto, l4, ident):
    """One pcap record on the fixed +1 ms timeline (idx = packet index)."""
    if src_ip == CLIENT_IP:
        src_mac, dst_mac = CLIENT_MAC, SERVER_MAC
    else:
        src_mac, dst_mac = SERVER_MAC, CLIENT_MAC
    frame = (dst_mac + src_mac + b"\x08\x00"
             + ipv4(src_ip, dst_ip, proto, len(l4), ident) + l4)
    pkt_hdr = struct.pack("<IIII", BASE_TS, idx * 1000, len(frame), len(frame))
    return pkt_hdr + frame


# ------------------------------------------------------------- payloads


HTTP_REQ = (b"GET /hello HTTP/1.1\r\n"
            b"Host: zeek.example.com\r\n"
            b"User-Agent: zeek-p1-test\r\n"
            b"Accept: */*\r\n"
            b"Connection: close\r\n"
            b"\r\n")

HTTP_RESP = (b"HTTP/1.1 200 OK\r\n"
             b"Content-Type: text/plain\r\n"
             b"Content-Length: 2\r\n"
             b"Connection: close\r\n"
             b"\r\n"
             b"ok")

SNI_NAME = b"zeek.example.com"  # 16 chars; asserted via ssl/dns/http events


def _client_hello():
    """TLS ClientHello with SNI: fixed legacy-1.2 record, supported_versions 1.3."""
    random32 = bytes(range(32))
    ciphers = b"\x13\x01\x13\x02\x00\x2f"  # three suites
    sni_ext = (b"\x00\x00"
               + struct.pack("!H", 21)          # extension length
               + struct.pack("!H", 19)          # server_name_list length
               + b"\x00"                        # host_name type
               + struct.pack("!H", len(SNI_NAME))
               + SNI_NAME)
    sv_ext = (b"\x00\x2b"
              + struct.pack("!H", 4)            # extension length
              + struct.pack("!H", 2)            # list length
              + b"\x03\x04")                    # TLS 1.3
    extensions = sni_ext + sv_ext
    body = (struct.pack("!H", 0x0303)           # legacy_version
            + random32
            + b"\x00"                           # session_id length
            + struct.pack("!H", len(ciphers)) + ciphers
            + b"\x01\x00"                       # compression: null
            + struct.pack("!H", len(extensions)) + extensions)
    handshake = b"\x01" + struct.pack("!I", len(body))[1:] + body
    return b"\x16\x03\x01" + struct.pack("!H", len(handshake)) + handshake


def _dns_qname():
    # "zeek.example.com"
    return b"\x04zeek\x07example\x03com\x00"


def _dns_query():
    hdr = struct.pack("!HHHHHH", 0x1234, 0x0100, 1, 0, 0, 0)  # RD, qdcount=1
    return hdr + _dns_qname() + b"\x00\x01\x00\x01"           # type A, class IN


def _dns_response():
    hdr = struct.pack("!HHHHHH", 0x1234, 0x8180, 1, 1, 0, 0)  # QR|RA|RD, ancount=1
    answer = (b"\xc0\x0c"                       # pointer to QNAME (offset 12)
              + struct.pack("!HHIH", 1, 1, 60, 4)
              + b"\xc0\x00\x02\x01")            # 192.0.2.1
    return hdr + _dns_qname() + answer


# ------------------------------------------------------------- flows


def _tcp_flow(cport, sport, c_isn, s_isn, req, resp=b""):
    """Full handshake + request (+ optional response) + client FIN close.

    Returns (c2s, l4) pairs in wire order: 7 packets without resp, 9 with.
    """
    l1, l2 = len(req), len(resp)
    pkts = []

    def put(c2s, seq, ack, flags, payload=b""):
        if c2s:
            pkts.append((True, tcp_seg(cport, sport, seq, ack, flags, payload)))
        else:
            pkts.append((False, tcp_seg(sport, cport, seq, ack, flags, payload)))

    put(True, c_isn, 0, F_SYN)
    put(False, s_isn, c_isn + 1, F_SYN | F_ACK)
    put(True, c_isn + 1, s_isn + 1, F_ACK)
    put(True, c_isn + 1, s_isn + 1, F_PSH | F_ACK, req)
    if resp:
        put(False, s_isn + 1, c_isn + 1 + l1, F_ACK)
        put(False, s_isn + 1, c_isn + 1 + l1, F_PSH | F_ACK, resp)
        put(True, c_isn + 1 + l1, s_isn + 1 + l2, F_ACK)
    put(True, c_isn + 1 + l1, s_isn + 1 + l2, F_FIN | F_ACK)
    put(False, s_isn + 1 + l2, c_isn + 2 + l1, F_ACK)
    return pkts


# ------------------------------------------------------------- main


def main():
    if len(sys.argv) > 1:
        out = sys.argv[1]
    else:
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "sample.pcap")

    pkts = []
    for c2s, l4 in _tcp_flow(A_SRC_PORT, A_DST_PORT, 1000, 5000,
                             HTTP_REQ, HTTP_RESP):
        pkts.append((c2s, PROTO_TCP, l4))
    for c2s, l4 in _tcp_flow(B_SRC_PORT, B_DST_PORT, 2000, 7000,
                             _client_hello()):
        pkts.append((c2s, PROTO_TCP, l4))
    pkts.append((True, PROTO_UDP, udp_seg(C_SRC_PORT, C_DST_PORT,
                                          _dns_query())))
    pkts.append((False, PROTO_UDP, udp_seg(C_DST_PORT, C_SRC_PORT,
                                           _dns_response())))

    with open(out, "wb") as f:
        f.write(pcap_global_header())
        for idx, (c2s, proto, l4) in enumerate(pkts):
            src, dst = (CLIENT_IP, SERVER_IP) if c2s else (SERVER_IP, CLIENT_IP)
            f.write(pcap_record(idx, src, dst, proto, l4, 0x0100 + idx))

    with open(out, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    print("wrote %s (%d packets, %d bytes)"
          % (out, len(pkts), os.path.getsize(out)))
    print("sha256 " + digest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
