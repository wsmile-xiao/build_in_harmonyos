// Consumer test for pcapplusplus/26.07.
//
// Uses only the public, installed API of the package: address types, packet
// crafting, wire serialization + re-parse, offline BPF filtering (through the
// bundled libpcap), and a pcap file write/read round-trip. A last block asserts
// platform properties that are specific to the HarmonyOS PC target.
//
// Prints "<passed>/<total> checks passed" which the test_package converts into
// HMBS_TEST_PACKAGE_RESULT.
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>

#include "EthLayer.h"
#include "IPv4Layer.h"
#include "IpAddress.h"
#include "MacAddress.h"
#include "Packet.h"
#include "PayloadLayer.h"
#include "PcapFileDevice.h"
#include "PcapFilter.h"
#include "PcapPlusPlusVersion.h"
#include "RawPacket.h"
#include "TcpLayer.h"

static int g_checks = 0;
static int g_failed = 0;

#define CHECK(cond, label)                                        \
    do {                                                          \
        ++g_checks;                                               \
        if (cond) {                                               \
            std::printf("ok   %2d - %s\n", g_checks, label);      \
        } else {                                                  \
            ++g_failed;                                           \
            std::printf("FAIL %2d - %s\n", g_checks, label);      \
        }                                                         \
    } while (0)

int main()
{
    std::printf("pcapplusplus consumer test, library version %s\n",
                pcpp::getPcapPlusPlusVersionFull().c_str());

    // ── version identity ───────────────────────────────────────────────────
    CHECK(pcpp::getPcapPlusPlusVersion() == "26.07", "getPcapPlusPlusVersion() == 26.07");
    CHECK(!pcpp::getPcapPlusPlusVersionFull().empty(), "full version string is available");

    // ── IPv4 address ───────────────────────────────────────────────────────
    pcpp::IPv4Address ip("192.168.10.7");
    CHECK(ip.toString() == "192.168.10.7", "IPv4Address parse/format round-trip");
    const uint32_t ipRaw = ip.toInt();
    CHECK(std::memcmp(&ipRaw, "\xc0\xa8\x0a\x07", 4) == 0,
          "IPv4Address::toInt() bytes are in network byte order");
    CHECK(ip.matchNetwork("192.168.10.0/24"), "IPv4Address::matchNetwork() CIDR form");
    CHECK(!pcpp::IPv4Address("10.0.0.1").isMulticast(), "unicast IPv4 is not multicast");
    CHECK(pcpp::IPv4Address("224.0.0.1").isMulticast(), "224.0.0.1 is multicast");
    CHECK(pcpp::IPv4Address::isValidIPv4Address("1.2.3.4"), "isValidIPv4Address(valid)");
    CHECK(!pcpp::IPv4Address::isValidIPv4Address("300.1.2.3"), "isValidIPv4Address(invalid)");

    // ── MAC address ────────────────────────────────────────────────────────
    pcpp::MacAddress mac("00:11:22:33:44:55");
    CHECK(mac.toString() == "00:11:22:33:44:55", "MacAddress parse/format round-trip");
    CHECK(mac.getRawData()[0] == 0x00 && mac.getRawData()[5] == 0x55,
          "MacAddress raw bytes are in wire order");
    CHECK(pcpp::MacAddress::Broadcast.toString() == "ff:ff:ff:ff:ff:ff",
          "MacAddress::Broadcast constant");
    CHECK(pcpp::MacAddress::Zero.toString() == "00:00:00:00:00:00", "MacAddress::Zero constant");

    // ── craft a packet, serialize it and re-parse the wire bytes ───────────
    const std::string payload = "PcapPlusPlus-OHOS";
    pcpp::EthLayer eth(pcpp::MacAddress("00:11:22:33:44:55"),
                       pcpp::MacAddress("66:77:88:99:aa:bb"), PCPP_ETHERTYPE_IP);
    pcpp::IPv4Layer ipLayer(ip, pcpp::IPv4Address("10.0.0.1"));
    pcpp::TcpLayer tcp(44321, 80);
    pcpp::PayloadLayer payloadLayer(reinterpret_cast<const uint8_t*>(payload.data()),
                                    payload.size());

    pcpp::Packet packet(100);
    CHECK(packet.addLayer(&eth), "Packet::addLayer(EthLayer)");
    CHECK(packet.addLayer(&ipLayer), "Packet::addLayer(IPv4Layer)");
    CHECK(packet.addLayer(&tcp), "Packet::addLayer(TcpLayer)");
    CHECK(packet.addLayer(&payloadLayer), "Packet::addLayer(PayloadLayer)");
    packet.computeCalculateFields();

    pcpp::RawPacket* raw = packet.getRawPacket();
    CHECK(raw != nullptr && raw->getRawDataLen() > 0, "packet serialized into a RawPacket");
    CHECK(raw != nullptr
              && raw->getRawDataLen() == static_cast<int>(14 + 20 + 20 + payload.size()),
          "wire length == Eth(14) + IPv4(20) + TCP(20) + payload");

    pcpp::Packet reparsed(raw);
    CHECK(reparsed.isPacketOfType(pcpp::Ethernet), "reparsed packet has an Ethernet layer");
    CHECK(reparsed.isPacketOfType(pcpp::IPv4), "reparsed packet has an IPv4 layer");
    CHECK(reparsed.isPacketOfType(pcpp::TCP), "reparsed packet has a TCP layer");
    pcpp::TcpLayer* reparsedTcp = reparsed.getLayerOfType<pcpp::TcpLayer>();
    CHECK(reparsedTcp != nullptr && reparsedTcp->getSrcPort() == 44321
              && reparsedTcp->getDstPort() == 80,
          "reparsed TCP source/destination ports survive the round-trip");
    pcpp::IPv4Layer* reparsedIp = reparsed.getLayerOfType<pcpp::IPv4Layer>();
    CHECK(reparsedIp != nullptr && reparsedIp->getSrcIPv4Address() == ip,
          "reparsed IPv4 source address survives the round-trip");

    // ── offline BPF filtering through libpcap ──────────────────────────────
    pcpp::BPFStringFilter tcpFilter("tcp");
    CHECK(tcpFilter.matches(*raw), "libpcap BPF 'tcp' matches the crafted TCP packet");
    pcpp::BPFStringFilter udpFilter("udp");
    CHECK(!udpFilter.matches(*raw), "libpcap BPF 'udp' rejects the crafted TCP packet");

    // ── pcap file write / read round-trip (no live device needed) ──────────
    const char* pcapFile = "pcapplusplus_consumer_roundtrip.pcap";
    {
        pcpp::PcapFileWriterDevice writer(pcapFile);
        CHECK(writer.open(), "PcapFileWriterDevice::open()");
        CHECK(writer.writePacket(*raw), "PcapFileWriterDevice::writePacket()");
        writer.close();
    }
    {
        pcpp::PcapFileReaderDevice reader(pcapFile);
        CHECK(reader.open(), "PcapFileReaderDevice::open()");
        pcpp::RawPacket readPacket;
        CHECK(reader.getNextPacket(readPacket), "PcapFileReaderDevice::getNextPacket()");
        CHECK(readPacket.getRawDataLen() == raw->getRawDataLen(),
              "pcap file round-trip preserves the packet length");
        reader.close();
    }
    std::remove(pcapFile);

    // ── HarmonyOS PC (target) specific properties ──────────────────────────
#ifdef __OHOS__
    CHECK(true, "compiled against the HarmonyOS target (__OHOS__ defined)");
#else
    CHECK(false, "compiled against the HarmonyOS target (__OHOS__ defined)");
#endif
    CHECK(sizeof(void*) == 8, "HarmonyOS aarch64: LP64 data model (sizeof(void*) == 8)");
    CHECK(sizeof(long) == 8, "HarmonyOS aarch64: sizeof(long) == 8");
    const uint16_t one = 1;
    CHECK(*reinterpret_cast<const uint8_t*>(&one) == 1, "HarmonyOS aarch64: little-endian");
    CHECK(sizeof(timespec) == 16, "HarmonyOS aarch64: 64-bit timespec");

    std::printf("test_pcapplusplus: %d/%d checks passed\n", g_checks - g_failed, g_checks);
    return g_failed == 0 ? 0 : 1;
}
