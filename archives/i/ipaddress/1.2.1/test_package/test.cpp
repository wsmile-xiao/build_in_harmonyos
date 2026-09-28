// test_package consumer test — real usage of the ipaddress library API (R34).
// Parses IPv4/IPv6 addresses/networks and verifies round-trip to string.
#include <ipaddress/ipv4-address.hpp>
#include <ipaddress/ipv6-address.hpp>
#include <ipaddress/ipv4-network.hpp>
#include <ipaddress/ipv6-network.hpp>

#include <cstdio>

using ipaddress::ipv4_address;
using ipaddress::ipv6_address;
using ipaddress::ipv4_network;
using ipaddress::ipv6_network;

int main() {
    // ipv4_address::parse() is constexpr; verify value + round-trip
    constexpr auto v4 = ipv4_address::parse("192.168.1.10");
    if (!(v4.to_string() == "192.168.1.10")) {
        std::printf("FAIL: ipv4 round-trip got %s\n", v4.to_string().c_str());
        return 1;
    }

    // ipv6_address::parse() round-trip
    constexpr auto v6 = ipv6_address::parse("2001:db8::1");
    if (!(v6.to_string() == "2001:db8::1")) {
        std::printf("FAIL: ipv6 round-trip got %s\n", v6.to_string().c_str());
        return 1;
    }

    // Network parse: address + prefix
    constexpr auto net4 = ipv4_network::parse("10.0.0.0/8");
    if (!(net4.to_string() == "10.0.0.0/8")) {
        std::printf("FAIL: ipv4 network round-trip got %s\n", net4.to_string().c_str());
        return 1;
    }

    constexpr auto net6 = ipv6_network::parse("2001:db8::/32");
    if (!(net6.to_string() == "2001:db8::/32")) {
        std::printf("FAIL: ipv6 network round-trip got %s\n", net6.to_string().c_str());
        return 1;
    }

    std::printf("ipaddress 1.2.1 consumer test: OK (v4=%s v6=%s net4=%s net6=%s)\n",
                v4.to_string().c_str(), v6.to_string().c_str(),
                net4.to_string().c_str(), net6.to_string().c_str());
    return 0;
}
