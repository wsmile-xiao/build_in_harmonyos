// test_package 消费者验证 — 实际调用 json11 C++ API（R34: test 必须实质依赖被测包）
#include <cassert>
#include <cstdio>
#include <string>

#include "json11.hpp"

using namespace json11;
using std::string;

int main() {
    string err;
    Json j = Json::parse(R"({"hello":"world","n":42,"flag":true})", err);
    assert(err.empty());
    assert(!j.is_null());
    assert(j["hello"].string_value() == "world");
    assert(j["n"].number_value() == 42.0);
    assert(j["flag"].bool_value() == true);
    string dump = j.dump();
    assert(dump.find("\"hello\": \"world\"") != string::npos);
    printf("json11 consumer test OK -> %s\n", dump.c_str());
    return 0;
}