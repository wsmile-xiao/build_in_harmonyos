// test_package consumer test — exercises the real ArduinoJson API (R34).
#include <ArduinoJson.h>
#include <cassert>
#include <cstdio>
#include <cstring>

int main() {
    JsonDocument doc;
    doc["hello"] = "world";
    doc["answer"] = 42;
    doc["pi"] = 3.14;

    // Serialization round-trip through the public API.
    std::string out;
    serializeJson(doc, out);
    assert(out.find("\"hello\":\"world\"") != std::string::npos);
    assert(out.find("\"answer\":42") != std::string::npos);

    // Deserialization of a nested document.
    JsonDocument in;
    DeserializationError err = deserializeJson(in,
        "{\"sensor\":{\"temp\":23.5,\"unit\":\"C\"},\"ok\":true}");
    assert(!err);
    assert(in["sensor"]["temp"].as<float>() == 23.5f);
    assert(strcmp(in["sensor"]["unit"], "C") == 0);
    assert(in["ok"].as<bool>() == true);

    // JsonVariant / containsKey paths.
    assert(doc.containsKey("hello"));
    assert(!doc["missing"].is<int>());

    // Version constant exposed by the header.
    assert(ARDUINOJSON_VERSION_MAJOR == 7);

    std::printf("arduinojson test_package: OK (7.4.2 API exercised)\n");
    return 0;
}
