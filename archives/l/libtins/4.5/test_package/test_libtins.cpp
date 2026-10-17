// Consumer test for libtins 4.5 (OHOS): uses the public API as a library
// consumer — crafts an Ethernet/IPv4/TCP PDU tree, serializes it, re-parses the
// wire bytes and asserts every field it checks. Exit code is decided by the
// assertions below (non-zero on the first failed check).
//
// Port arguments follow the upstream signatures: TCP/UDP take (dport, sport),
// IP/EthernetII take (dst, src).
#include <tins/ethernetII.h>
#include <tins/hw_address.h>
#include <tins/ip.h>
#include <tins/ip_address.h>
#include <tins/pdu.h>
#include <tins/rawpdu.h>
#include <tins/tcp.h>
#include <tins/udp.h>

#include <cstdio>
#include <string>

using namespace Tins;

static int checks = 0;

#define CHECK(cond)                                                          \
    do {                                                                     \
        if (!(cond)) {                                                       \
            std::fprintf(stderr, "FAILED: %s (line %d)\n", #cond, __LINE__);  \
            return 1;                                                        \
        }                                                                    \
        ++checks;                                                            \
    } while (0)

int main() {
    const std::string payload("libtins-ohos");

    // 1) craft EthernetII / IPv4 / TCP / RawPDU by chaining PDUs
    EthernetII crafted = EthernetII("66:77:88:99:aa:bb", "00:11:22:33:44:55")
                       / IP("10.0.0.1", "192.168.10.1")
                       / TCP(443, 43210)
                       / RawPDU(payload);
    TCP& tcp = crafted.rfind_pdu<TCP>();
    tcp.set_flag(TCP::SYN, 1);
    CHECK(tcp.dport() == 443);
    CHECK(tcp.sport() == 43210);
    CHECK(tcp.flags() == TCP::SYN);
    CHECK(crafted.rfind_pdu<TCP>().inner_pdu() != nullptr);

    // 2) serialize the whole stack to wire bytes
    PDU::serialization_type raw = crafted.serialize();
    // 14 (EthernetII) + 20 (IPv4, no options) + 20 (TCP, no options) + payload
    CHECK(raw.size() == 14u + 20u + 20u + payload.size());

    // 3) parse the serialized bytes back and validate the decoded fields
    EthernetII parsed(&raw[0], static_cast<uint32_t>(raw.size()));
    CHECK(parsed.dst_addr() == HWAddress<6>("66:77:88:99:aa:bb"));
    CHECK(parsed.src_addr() == HWAddress<6>("00:11:22:33:44:55"));

    IP& ip = parsed.rfind_pdu<IP>();
    CHECK(ip.dst_addr() == IPv4Address("10.0.0.1"));
    CHECK(ip.src_addr() == IPv4Address("192.168.10.1"));

    TCP& parsed_tcp = parsed.rfind_pdu<TCP>();
    CHECK(parsed_tcp.dport() == 443);
    CHECK(parsed_tcp.sport() == 43210);
    CHECK(parsed_tcp.flags() == TCP::SYN);

    RawPDU& parsed_payload = parsed.rfind_pdu<RawPDU>();
    const RawPDU::payload_type& bytes = parsed_payload.payload();
    CHECK(bytes.size() == payload.size());
    CHECK(std::string(bytes.begin(), bytes.end()) == payload);

    // 4) a second protocol stack (UDP) exercises the PDU chaining independently.
    // The payload keeps the frame above the 60-byte Ethernet minimum so the
    // serialized size is exactly headers + payload (no trailing padding).
    const std::string udp_payload("dns-query-payload-0123456");
    EthernetII udp_frame = EthernetII("66:77:88:99:aa:bb", "00:11:22:33:44:55")
                         / IP("10.1.1.2", "10.1.1.1")
                         / UDP(53, 5353)
                         / RawPDU(udp_payload);
    PDU::serialization_type udp_raw = udp_frame.serialize();
    CHECK(udp_raw.size() == 14u + 20u + 8u + udp_payload.size());
    EthernetII udp_parsed(&udp_raw[0], static_cast<uint32_t>(udp_raw.size()));
    CHECK(udp_parsed.rfind_pdu<UDP>().dport() == 53);
    CHECK(udp_parsed.rfind_pdu<UDP>().sport() == 5353);

    std::printf("test_libtins: %d checks passed\n", checks);
    return 0;
}
