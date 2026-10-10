/*
 * Consumer-view test for isc-kea 3.0.3.
 *
 * Links against the packaged Kea libraries and exercises the public API the
 * way an embedded consumer does: IOAddress (libkea-asiolink) construction /
 * text round-trip / family classification, Element (libkea-cc) JSON parsing
 * and mutation.
 */
#include <asiolink/io_address.h>
#include <cc/data.h>

#include <iostream>
#include <string>

using namespace isc;
using namespace isc::asiolink;
using namespace isc::data;

namespace {

int failures = 0;

void
check(bool ok, const std::string& what) {
    std::cout << (ok ? "ok  " : "FAIL") << " - " << what << "\n";
    std::cout.flush();
    if (!ok) {
        ++failures;
    }

}

} // namespace

int
main() {
    // 1) libkea-asiolink: IOAddress round-trip and family classification.
    const IOAddress v4("192.0.2.1");
    const IOAddress v6("2001:db8::1");
    check(v4.toText() == "192.0.2.1", "IOAddress v4 toText() round-trips");
    check(v6.toText() == "2001:db8::1", "IOAddress v6 toText() round-trips");
    check(v4.isV4() && !v4.isV6(), "IOAddress v4 family is v4");
    check(v6.isV6() && !v6.isV4(), "IOAddress v6 family is v6");
    check(IOAddress("0.0.0.0").isV4Zero(), "IOAddress isV4Zero() recognizes 0.0.0.0");

    // 2) libkea-cc: Element JSON parsing and mutation (the wire every Kea
    //    component speaks, from kea-dhcp4 config to hook library params).
    ElementPtr config = Element::fromJSON("{\"dhcp4\": {\"port\": 67}, \"valid-lifetime\": 3600}");
    check(config && config->contains("dhcp4"), "Element::fromJSON() parses an object");
    ConstElementPtr dhcp4 = config->get("dhcp4");
    check(dhcp4 && dhcp4->contains("port"), "nested object element is reachable");
    check(dhcp4->get("port")->intValue() == 67, "intValue() reads the parsed port");
    check(config->get("valid-lifetime")->intValue() == 3600, "intValue() reads valid-lifetime");
    config->set("renew-timer", Element::create(static_cast<long long int>(900)));
    check(config->get("renew-timer")->intValue() == 900, "set()/create() mutates the tree");
    check(Element::fromJSON("[1, 2, 3]")->size() == 3, "fromJSON() parses a list");

    std::cout << (failures == 0 ? "PASS" : "FAILED") << ": test_isc_kea\n";
    return failures == 0 ? 0 : 1;
}
