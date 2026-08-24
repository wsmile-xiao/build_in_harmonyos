#include <google/protobuf/any.pb.h>
#include <google/protobuf/arena.h>
#include <google/protobuf/struct.pb.h>
#include <google/protobuf/timestamp.pb.h>
#include <google/protobuf/util/json_util.h>

#include <cstdio>
#include <string>

namespace {

int checks = 0;

#define CHECK_TRUE(condition)                                                   \
    do {                                                                        \
        if (!(condition)) {                                                     \
            std::fprintf(stderr, "check failed at line %d: %s\n", __LINE__,   \
                         #condition);                                           \
            return 1;                                                           \
        }                                                                       \
        ++checks;                                                               \
    } while (false)

int TestAny() {
    google::protobuf::Timestamp input;
    input.set_seconds(1'234'567);
    input.set_nanos(890);

    google::protobuf::Any any;
    CHECK_TRUE(any.PackFrom(input));
    CHECK_TRUE(any.Is<google::protobuf::Timestamp>());

    google::protobuf::Timestamp output;
    CHECK_TRUE(any.UnpackTo(&output));
    CHECK_TRUE(output.seconds() == input.seconds());
    CHECK_TRUE(output.nanos() == input.nanos());
    return 0;
}

int TestSerialize() {
    google::protobuf::Struct input;
    (*input.mutable_fields())["name"].set_string_value("HarmonyOS");
    (*input.mutable_fields())["answer"].set_number_value(42.0);

    std::string wire;
    CHECK_TRUE(input.SerializeToString(&wire));
    CHECK_TRUE(!wire.empty());

    google::protobuf::Struct output;
    CHECK_TRUE(output.ParseFromString(wire));
    CHECK_TRUE(output.fields().size() == 2);
    CHECK_TRUE(output.fields().at("name").string_value() == "HarmonyOS");
    return 0;
}

int TestJson() {
    google::protobuf::Struct input;
    (*input.mutable_fields())["enabled"].set_bool_value(true);
    (*input.mutable_fields())["count"].set_number_value(3.0);

    std::string json;
    CHECK_TRUE(google::protobuf::util::MessageToJsonString(input, &json).ok());
    CHECK_TRUE(json.find("enabled") != std::string::npos);

    google::protobuf::Struct output;
    CHECK_TRUE(google::protobuf::util::JsonStringToMessage(json, &output).ok());
    CHECK_TRUE(output.fields().at("enabled").bool_value());
    CHECK_TRUE(output.fields().at("count").number_value() == 3.0);
    return 0;
}

int TestArena() {
    google::protobuf::Arena arena;
    auto* value = google::protobuf::Arena::Create<google::protobuf::Struct>(&arena);
    CHECK_TRUE(value != nullptr);
    (*value->mutable_fields())["platform"].set_string_value("OpenHarmony");
    CHECK_TRUE(value->fields().at("platform").string_value() == "OpenHarmony");
    CHECK_TRUE(arena.SpaceAllocated() > 0);
    CHECK_TRUE(arena.Reset() > 0);
    return 0;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        std::fprintf(stderr, "usage: %s any|serialize|json|arena\n", argv[0]);
        return 2;
    }

    const std::string mode(argv[1]);
    int result = 2;
    if (mode == "any") {
        result = TestAny();
    } else if (mode == "serialize") {
        result = TestSerialize();
    } else if (mode == "json") {
        result = TestJson();
    } else if (mode == "arena") {
        result = TestArena();
    } else {
        std::fprintf(stderr, "unknown test mode: %s\n", mode.c_str());
        return 2;
    }

    if (result == 0) {
        std::printf("protobuf %s: %d assertions passed\n", mode.c_str(), checks);
    }
    return result;
}
