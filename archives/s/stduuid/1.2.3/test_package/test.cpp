#include <cassert>
#include <cstdio>
#include <string>
#include <vector>
#include <set>

#include <uuid.h>

int main() {
    // 1) Default-constructed uuid must be nil.
    uuids::uuid nil;
    assert(nil.is_nil());
    assert(uuids::to_string(nil) == "00000000-0000-0000-0000-000000000000");

    // 2) Random generator produces version-4 UUIDs that are all distinct.
    std::random_device rd;
    std::mt19937_64 engine(rd());
    auto generator = uuids::basic_uuid_random_generator<std::mt19937_64>(engine);
    std::set<std::string> seen;
    for (int i = 0; i < 100; ++i) {
        uuids::uuid id = generator();
        assert(!id.is_nil());
        assert(id.version() == uuids::uuid_version::random_number_based);
        assert(id.variant() == uuids::uuid_variant::rfc);
        std::string s = uuids::to_string(id);
        assert(s.size() == 36);
        assert(s[8] == '-' && s[13] == '-' && s[18] == '-' && s[23] == '-');
        seen.insert(s);
    }
    assert(seen.size() == 100);

    // 3) String round-trip.
    std::string orig = "47183823-2574-4bfd-b411-99ed177d3e43";
    uuids::uuid parsed = uuids::uuid::from_string(orig).value();
    assert(uuids::to_string(parsed) == orig);

    // 4) Equality and ordering.
    assert(parsed == parsed);
    assert(!(parsed < parsed));

    std::printf("test stduuid 1.2.3 (C++17 UUID API): OK (%zu distinct v4 uuids)\n",
                seen.size());
    return 0;
}
