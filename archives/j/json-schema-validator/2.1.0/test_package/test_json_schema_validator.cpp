// test_json_schema_validator.cpp — smoke test for json-schema-validator 2.1.0
// Validates a minimal draft-7 schema against a conforming and a non-conforming
// instance, exercising the public nlohmann::json_schema::json_validator API.

#include <nlohmann/json-schema.hpp>

#include <iostream>
#include <string>

using nlohmann::json;
using nlohmann::json_schema::json_validator;

int main() {
    json schema = R"({
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "name": { "type": "string" },
            "age": { "type": "integer", "minimum": 0 }
        },
        "required": ["name"]
    })"_json;

    json ok = R"({ "name": "alice", "age": 30 })"_json;
    json bad = R"({ "name": "bob", "age": -5 })"_json;

    json_validator validator;
    validator.set_root_schema(schema);

    validator.validate(ok);
    std::cout << "PASS: conforming instance accepted\n";

    bool rejected = false;
    try {
        validator.validate(bad);
    } catch (const std::exception &e) {
        rejected = true;
        std::cout << "PASS: non-conforming instance rejected (" << e.what() << ")\n";
    }
    if (!rejected) {
        std::cerr << "FAIL: non-conforming instance was not rejected\n";
        return 1;
    }
    std::cout << "json-schema-validator smoke test OK\n";
    return 0;
}
