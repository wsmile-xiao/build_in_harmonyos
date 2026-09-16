// test_ccrtp.cpp — consumer smoke test for GNU ccRTP 2.1.2
//
// Exercises real ccrtp APIs on OHOS:
//   * InetHostAddress (from GNU uCommon / Common C++): construct a
//     loopback address from a dotted-quad string and validate it.
//   * IncomingRTPPkt: parse a minimal raw RTP packet and verify the
//     header fields (validity, protocol version, payload type, padding
//     flag, raw packet size) round-trip through the library.
//
// Note: IncomingRTPPkt takes ownership of the packet buffer (its base
// destructor runs `delete [] buffer`), so the buffer must be heap-allocated.
#include <ccrtp/rtp.h>
#include <ccrtp/rtppkt.h>

#include <cstdio>
#include <cstring>

// ccRTP exposes its classes in the Common C++ "ost" namespace.
using namespace ost;

int main() {
    // --- InetHostAddress (ucommon/Common C++ API) ---
    InetHostAddress loopback("127.0.0.1");
    if (!loopback.isInetAddress()) {
        printf("FAIL: InetHostAddress(\"127.0.0.1\") is not a valid address\n");
        return 1;
    }

    // --- RTP packet parsing ---
    // Minimal valid RTP packet: 12-byte fixed header + 8-byte payload.
    unsigned char* raw = new unsigned char[20];
    std::memset(raw, 0, 20);
    raw[0] = 0x80;                                    // version 2, no CSRC/ext/pad
    raw[1] = 0x08;                                    // payload type 8 (PCMA), marker clear
    raw[2] = 0x12; raw[3] = 0x34;                     // sequence 0x1234 (net order)
    raw[4] = 0xde; raw[5] = 0xad; raw[6] = 0xbe; raw[7] = 0xef;  // timestamp
    raw[8] = 0xca; raw[9] = 0xfe; raw[10] = 0xba; raw[11] = 0xbe; // SSRC

    {
        IncomingRTPPkt pkt(raw, 20);
        if (!pkt.isHeaderValid()) {
            printf("FAIL: RTP header is invalid\n");
            return 1;
        }
        if (pkt.getProtocolVersion() != 2) {
            printf("FAIL: RTP protocol version != 2\n");
            return 1;
        }
        if (pkt.getPayloadType() != 8) {
            printf("FAIL: RTP payload type != 8\n");
            return 1;
        }
        if (pkt.isPadded()) {
            printf("FAIL: padding bit unexpectedly set\n");
            return 1;
        }
        if (pkt.getRawPacketSize() != 20) {
            printf("FAIL: raw packet size mismatch (%d != 20)\n",
                   (int)pkt.getRawPacketSize());
            return 1;
        }
        // pkt owns `raw` and releases it on destruction.
    }

    printf("ccrtp smoke test OK (InetHostAddress + IncomingRTPPkt)\n");
    return 0;
}
