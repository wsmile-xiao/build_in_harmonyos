#include <cstdint>
#include <cstdio>
#include <string>
#include <vector>

#include "flatbuffers/flatbuffers.h"
#include "flatbuffers/flexbuffers.h"

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
    // 1) FlatBufferBuilder + CreateVector + GetRoot<Vector<int32_t>> round trip.
    flatbuffers::FlatBufferBuilder builder;
    const std::vector<int32_t> values = {7, -3, 42};
    auto vec_off = builder.CreateVector(values);
    builder.Finish(vec_off);
    CHECK(builder.GetSize() > 0);
    auto root =
        flatbuffers::GetRoot<flatbuffers::Vector<int32_t>>(builder.GetBufferPointer());
    CHECK(root->size() == 3);
    CHECK(root->Get(0) == 7);
    CHECK(root->Get(1) == -3);
    CHECK(root->Get(2) == 42);

    // 2) flexbuffers map round trip.
    flexbuffers::Builder fbb;
    auto map_ref = fbb.StartMap();
    fbb.Key("name");
    fbb.String("harmony");
    fbb.Key("count");
    fbb.Int(25);
    fbb.Key("ratio");
    fbb.Double(0.5);
    fbb.EndMap(map_ref);
    fbb.Finish();
    const auto &blob = fbb.GetBuffer();
    auto parsed = flexbuffers::GetRoot(blob.data(), blob.size());
    CHECK(parsed.IsMap());
    auto m = parsed.AsMap();
    CHECK(m.size() == 3);
    CHECK(std::string(m["name"].AsString().c_str()) == "harmony");
    CHECK(m["count"].AsInt32() == 25);
    CHECK(m["ratio"].AsDouble() == 0.5);

    std::printf("test_flatbuffers consumer: OK (%d checks)\n", g_checks);
    return 0;
}
