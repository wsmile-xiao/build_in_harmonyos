// test_package consumer test for univalue 1.1.1
// Exercises the real public API: UniValue::read / write / type inspection,
// linking against the installed libunivalue.
#include <univalue.h>

#include <cstdio>
#include <string>

static int failures = 0;

static void expect(bool cond, const char* what) {
    if (!cond) {
        std::printf("FAIL: %s\n", what);
        failures++;
    } else {
        std::printf("PASS: %s\n", what);
    }
}

int main() {
    // Parse a JSON object and inspect values through the public API.
    const char* json =
        "{\"name\":\"univalue\",\"version\":1.1,\"enabled\":true,\"pi\":3.14159,"
        "\"tags\":[\"json\",\"c++\"]}";
    UniValue obj;
    expect(obj.read(json), "read nested JSON object");

    expect(obj.isObject(), "parsed value is an object");
    expect(obj.exists("name"), "object has key 'name'");
    expect(obj.exists("version"), "object has key 'version'");
    expect(obj["name"].getValStr() == "univalue", "string member value preserved");

    // Round-trip: write what we read, then re-parse.
    std::string written = obj.write();
    UniValue reparsed;
    expect(reparsed.read(written), "re-parse serialized output");
    expect(reparsed.isObject(), "reparsed value is an object");

    // Array value.
    expect(obj.exists("tags"), "object has key 'tags'");
    expect(obj["tags"].isArray(), "'tags' is an array");
    expect(obj["tags"].size() == 2, "'tags' array has 2 elements");

    // Simple scalar parse + write round-trip.
    UniValue num;
    expect(num.read("42"), "read integer scalar");
    expect(num.isNum() && num.getValStr() == "42", "integer scalar value preserved");
    expect(num.write() == "42", "integer scalar serializes back to 42");

    if (failures == 0) {
        std::printf("test_univalue: all checks passed\n");
        return 0;
    }
    std::printf("test_univalue: %d check(s) failed\n", failures);
    return 1;
}