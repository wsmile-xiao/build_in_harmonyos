#include <cstdint>
#include <cstdio>
#include <string>

#include <osmium/builder/osm_object_builder.hpp>
#include <osmium/memory/buffer.hpp>
#include <osmium/osm/location.hpp>
#include <osmium/osm/node.hpp>
#include <osmium/osm/timestamp.hpp>
#include <osmium/version.hpp>

static int g_checks = 0;

#define CHECK(cond)                                                            \
    do {                                                                       \
        if (!(cond)) {                                                         \
            std::printf("CONSUMER CHECK FAILED: %s (line %d)\n", #cond,        \
                        __LINE__);                                             \
            return 1;                                                          \
        }                                                                      \
        g_checks++;                                                            \
    } while (0)

int main() {
    // Version contract of the installed package.
    CHECK(std::string(LIBOSMIUM_VERSION_STRING) == "2.23.0");

    // Real OSM data model round trip via the builder pattern: objects are
    // created inside an osmium memory buffer and read back afterwards.
    osmium::memory::Buffer buf(10240);
    {
        osmium::builder::NodeBuilder node_builder(buf);
        node_builder.set_id(42);
        node_builder.set_version(3);
        node_builder.set_timestamp(osmium::Timestamp(1700000000));
        node_builder.set_location(osmium::Location(13.737662, 51.050408));
        node_builder.set_user("ohos-tester");
    }

    const osmium::Node &node = buf.get<osmium::Node>(0);
    CHECK(node.id() == 42);
    CHECK(node.version() == 3);
    CHECK(node.visible());
    CHECK(node.timestamp().seconds_since_epoch() == 1700000000u);
    CHECK(node.location().lat() == 51.050408);
    CHECK(node.location().lon() == 13.737662);
    CHECK(std::string(node.user()) == "ohos-tester");

    std::printf("test_libosmium consumer: OK (%d checks)\n", g_checks);
    return 0;
}
