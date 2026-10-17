// test_jsonxx.cpp — Conan L1 consumer test for jsonxx 1.0.1
// 实际调用 jsonxx API：解析 JSON 文档、读写 Object/Array/Number/String。
// 注意：不依赖 assert()/NDEBUG 语义，所有检查在 Release 下同样执行。
#include <jsonxx.h>

#include <cmath>
#include <iostream>
#include <sstream>
#include <string>

static int failures = 0;

static bool nearly_equal(double a, double b) {
    return std::fabs(a - b) < 1e-9;
}

#define CHECK(cond)                                  \
    do {                                             \
        if (!(cond)) {                               \
            std::cerr << "FAIL: " #cond << std::endl; \
            ++failures;                              \
        }                                            \
    } while (0)

int main() {
    // 1. 解析 JSON 对象并读取各类型字段
    const std::string input =
        "{\"name\":\"harmony\",\"count\":42,\"ratio\":3.14,"
        "\"tags\":[\"c++\",\"json\"],\"ok\":true,\"empty_obj\":{}}";
    jsonxx::Object obj;
    CHECK(obj.parse(input));
    CHECK(obj.has<jsonxx::String>("name"));
    CHECK(obj.get<jsonxx::String>("name") == "harmony");
    CHECK(obj.has<jsonxx::Number>("count"));
    CHECK(obj.get<jsonxx::Number>("count") == 42);
    CHECK(obj.has<jsonxx::Number>("ratio"));
    CHECK(nearly_equal(obj.get<jsonxx::Number>("ratio"), 3.14));
    CHECK(obj.has<jsonxx::Array>("tags"));
    const jsonxx::Array& tags = obj.get<jsonxx::Array>("tags");
    CHECK(tags.size() == 2);
    CHECK(tags.get<jsonxx::String>(0) == "c++");
    CHECK(tags.get<jsonxx::String>(1) == "json");
    CHECK(obj.has<jsonxx::Boolean>("ok"));
    CHECK(obj.get<jsonxx::Boolean>("ok") == true);

    // 2. 从 istream 解析（实例方法）
    std::istringstream iss("{\"k\":[1,2,3]}");
    jsonxx::Object obj2;
    CHECK(obj2.parse(iss));
    CHECK(obj2.has<jsonxx::Array>("k"));
    CHECK(obj2.get<jsonxx::Array>("k").size() == 3);

    // 3. 动态构造并序列化
    jsonxx::Object out;
    out << "greeting" << "hello";
    out << "number" << 7;
    std::string serialized = out.json();
    jsonxx::Object roundtrip;
    CHECK(roundtrip.parse(serialized));
    CHECK(roundtrip.has<jsonxx::String>("greeting"));
    CHECK(roundtrip.get<jsonxx::String>("greeting") == "hello");
    CHECK(roundtrip.has<jsonxx::Number>("number"));
    CHECK(roundtrip.get<jsonxx::Number>("number") == 7);

    if (failures == 0) {
        std::cout << "test_jsonxx: OK" << std::endl;
        return 0;
    }
    std::cerr << "test_jsonxx: " << failures << " check(s) failed" << std::endl;
    return 1;
}