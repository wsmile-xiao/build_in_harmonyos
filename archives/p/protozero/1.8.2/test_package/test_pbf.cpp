// test_package consumer test — actually exercises the protozero API.
// Builds a minimal PBF message with pbf_writer, then decodes it back with
// pbf_reader and asserts field values (R34: must substantively use the package).
//
// NOTE: protozero getters ADVANCE the reader state, so they must always be
// called regardless of NDEBUG. Calling them only inside assert(...) would make
// the whole call disappear under -DNDEBUG (conan-verify uses -O3 -DNDEBUG),
// desynchronize the reader and throw invalid_tag_exception. Therefore every
// getter runs unconditionally and results are checked on saved variables.
#include <cassert>
#include <iostream>
#include <string>
#include <vector>

#include <protozero/pbf_reader.hpp>
#include <protozero/pbf_writer.hpp>

int main() {
    // 1) Encode: field 1 = varint (uint32), field 2 = string, field 3 = packed.
    // The writer and the packed sub-writer are scoped so that the packed
    // submessage is committed (close_submessage in destructor) before the
    // buffer is read back.
    std::string buffer;
    {
        protozero::pbf_writer writer(buffer);
        writer.add_uint32(1, 42u);
        writer.add_string(2, "hello protozero");
        {
            protozero::packed_field_uint32 packed(writer, 3);
            packed.add_element(1u);
            packed.add_element(2u);
            packed.add_element(3u);
        } // packed sub-writer commits here
    } // writer commits outer message here

    // 2) Decode back with pbf_reader and verify contents
    protozero::pbf_reader reader(buffer.data(), buffer.size());
    bool saw_field1 = false;
    bool saw_field2 = false;
    bool saw_field3 = false;
    uint32_t v1 = 0;
    std::string s2;
    std::vector<uint32_t> values;
    while (reader.next()) {
        switch (reader.tag()) {
        case 1:
            v1 = reader.get_uint32();  // always call getter (advances reader)
            saw_field1 = true;
            break;
        case 2:
            s2 = reader.get_string();  // always call getter (advances reader)
            saw_field2 = true;
            break;
        case 3: {
            // get_packed_uint32() returns an iterator_range of values
            for (auto v : reader.get_packed_uint32()) {
                values.push_back(v);
            }
            saw_field3 = true;
            break;
        }
        default:
            reader.skip();
        }
    }
    assert(saw_field1 && saw_field2 && saw_field3);
    assert(v1 == 42u);
    assert(s2 == "hello protozero");
    assert((values == std::vector<uint32_t>{1u, 2u, 3u}));

    std::cout << "protozero 1.8.2 test_package: OK (encode/decode roundtrip passed)\n";
    return 0;
}