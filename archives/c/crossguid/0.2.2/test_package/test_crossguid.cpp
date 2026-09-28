// Consumer test for crossguid/0.2.2 — uses only the installed public API:
// xg::newGuid(), xg::Guid(string), Guid::str(), operator<<, ==/!=, isValid().
#include "Guid.hpp"
#include <iostream>
#include <sstream>

int main()
{
    // 1) Generate three GUIDs via the public factory and verify uniqueness.
    auto g1 = xg::newGuid();
    auto g2 = xg::newGuid();
    auto g3 = xg::newGuid();
    if (g1 == g2 || g1 == g3 || g2 == g3) {
        std::cerr << "FAIL: generated GUIDs are not unique" << std::endl;
        return 1;
    }

    // 2) Parse a known GUID string and round-trip it via operator<< and str().
    xg::Guid parsed("7bcd757f-5b10-4f9b-af69-1a1f226f3b3e");
    if (!parsed.isValid()) {
        std::cerr << "FAIL: parsed GUID is invalid" << std::endl;
        return 1;
    }
    std::stringstream ss;
    ss << parsed;
    if (ss.str() != "7bcd757f-5b10-4f9b-af69-1a1f226f3b3e") {
        std::cerr << "FAIL: stream round-trip mismatch: " << ss.str() << std::endl;
        return 1;
    }
    if (parsed.str() != "7bcd757f-5b10-4f9b-af69-1a1f226f3b3e") {
        std::cerr << "FAIL: str() round-trip mismatch: " << parsed.str() << std::endl;
        return 1;
    }

    // 3) Equality semantics on equal strings.
    xg::Guid same("7bcd757f-5b10-4f9b-af69-1a1f226f3b3e");
    if (!(parsed == same) || parsed != same) {
        std::cerr << "FAIL: equality semantics broken" << std::endl;
        return 1;
    }

    std::cout << "consumer ok: newGuid unique, parse/round-trip, equality"
              << std::endl;
    return 0;
}
