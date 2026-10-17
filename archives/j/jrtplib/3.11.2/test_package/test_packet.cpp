#include <jrtplib3/rtprawpacket.h>
#include <jrtplib3/rtppacket.h>
#include <jrtplib3/rtpipv4address.h>
#include <jrtplib3/rtptimeutilities.h>

#include <cstdint>
#include <cstring>
#include <iostream>

namespace {

int s_failures = 0;

void check(bool ok, const char *name)
{
    std::cout << (ok ? "[PASS] " : "[FAIL] ") << name << std::endl;
    if (!ok) {
        ++s_failures;
    }
}

} // namespace

int main()
{
    // RTP header: V=2, P=0, X=0, CC=0, M=0, PT=0, seq=1234, ts=5678,
    // ssrc=0x11223344, followed by the 10-byte payload "1234567890".
    // Memory ownership mirrors upstream tests/testrawpacket.cpp: the raw
    // packet adopts the new[]'d buffer and address and releases them.
    const char payload[] = "1234567890";
    const uint8_t header[12] = {
        0x80, 0x00, 0x04, 0xD2, 0x00, 0x00, 0x16, 0x2E, 0x11, 0x22, 0x33, 0x44
    };
    const size_t totalLen = sizeof(header) + 10;
    uint8_t *data = new uint8_t[totalLen];
    std::memcpy(data, header, sizeof(header));
    std::memcpy(data + sizeof(header), payload, 10);

    jrtplib::RTPTime now = jrtplib::RTPTime::CurrentTime();
    jrtplib::RTPRawPacket raw(data, totalLen,
                              new jrtplib::RTPIPv4Address(0x7f000001, 5000), now);
    check(raw.IsRTP(), "raw-packet-recognized-as-rtp");

    jrtplib::RTPPacket parsed(raw);
    check(parsed.GetCreationError() == 0, "packet-parse-no-error");
    check(parsed.GetPacketLength() == totalLen, "packet-length-preserved");
    // GetPacketData() returns the entire packet (header + payload), so it
    // must round-trip against the assembled 'data' buffer. Comparing only
    // against the 12-byte 'header' with totalLen would read past the end
    // of 'header' (out-of-bounds) and always mismatch the payload bytes.
    check(parsed.GetPacketData() != 0 &&
          std::memcmp(parsed.GetPacketData(), data, totalLen) == 0,
          "packet-data-intact");
    check(parsed.GetPayloadLength() == 10, "packet-payload-length");
    check(parsed.GetPayloadData() != 0 &&
          std::memcmp(parsed.GetPayloadData(), payload, 10) == 0,
          "packet-payload-intact");

    // Negative case: a packet-type byte in the RTCP range (200) with a
    // long enough buffer must not be classified as RTP.
    uint8_t *bad = new uint8_t[totalLen];
    std::memcpy(bad, data, totalLen);
    bad[1] = 200;
    jrtplib::RTPTime later = jrtplib::RTPTime::CurrentTime();
    jrtplib::RTPRawPacket rawBad(bad, totalLen,
                                 new jrtplib::RTPIPv4Address(0x7f000001, 5001), later);
    check(!rawBad.IsRTP(), "rtcp-type-byte-not-rtp");

    if (s_failures != 0) {
        std::cerr << s_failures << " check(s) failed" << std::endl;
        return 1;
    }
    std::cout << "test_packet: all 7 checks passed" << std::endl;
    return 0;
}
