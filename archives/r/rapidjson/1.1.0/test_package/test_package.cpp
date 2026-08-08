// test_package.cpp — Substantive test for RapidJSON
// Verifies DOM parsing, value access, and JSON generation via RapidJSON API.
// This is a downstream-consumer test (Conan L1), not upstream's full test suite.

#include <rapidjson/document.h>
#include <rapidjson/writer.h>
#include <rapidjson/stringbuffer.h>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <utility>

static int failures = 0;
static const char *last_test = "";

#define TEST(name) do { last_test = name; } while(0)
#define ASSERT_EQ(a, b) do { \
    if ((a) != (b)) { \
        fprintf(stderr, "FAIL [%s] line %d: expected %d, got %d\n", \
                last_test, __LINE__, (int)(b), (int)(a)); \
        failures++; \
    } \
} while(0)
#define ASSERT_STREQ(a, b) do { \
    if (strcmp((a), (b)) != 0) { \
        fprintf(stderr, "FAIL [%s] line %d: expected \"%s\", got \"%s\"\n", \
                last_test, __LINE__, (b), (a)); \
        failures++; \
    } \
} while(0)
#define ASSERT_TRUE(cond) do { \
    if (!(cond)) { \
        fprintf(stderr, "FAIL [%s] line %d: condition false\n", \
                last_test, __LINE__); \
        failures++; \
    } \
} while(0)
#define ASSERT_FALSE(cond) ASSERT_TRUE(!(cond))

// Test 1: Parse a simple JSON object
static void test_parse_object() {
    TEST("parse_object");
    const char *json = "{\"hello\":\"world\",\"t\":true,\"f\":false,\"n\":null,"
                        "\"i\":123,\"pi\":3.14}";
    rapidjson::Document doc;
    doc.Parse(json);
    ASSERT_FALSE(doc.HasParseError());
    ASSERT_TRUE(doc.IsObject());
    ASSERT_TRUE(doc.HasMember("hello"));
    ASSERT_STREQ(doc["hello"].GetString(), "world");
    ASSERT_TRUE(doc["t"].IsTrue());
    ASSERT_TRUE(doc["f"].IsFalse());
    ASSERT_TRUE(doc["n"].IsNull());
    ASSERT_EQ(doc["i"].GetInt(), 123);
}

// Test 2: Parse a JSON array
static void test_parse_array() {
    TEST("parse_array");
    const char *json = "[1, 2, 3, 4, 5]";
    rapidjson::Document doc;
    doc.Parse(json);
    ASSERT_FALSE(doc.HasParseError());
    ASSERT_TRUE(doc.IsArray());
    ASSERT_EQ(doc.Size(), 5u);
    ASSERT_EQ(doc[0].GetInt(), 1);
    ASSERT_EQ(doc[4].GetInt(), 5);
}

// Test 3: Generate JSON with Writer
static void test_write_json() {
    TEST("write_json");
    rapidjson::StringBuffer sb;
    rapidjson::Writer<rapidjson::StringBuffer> writer(sb);

    writer.StartObject();
    writer.Key("name");
    writer.String("RapidJSON");
    writer.Key("version");
    writer.Int(1);
    writer.Key("features");
    writer.StartArray();
    writer.String("SAX");
    writer.String("DOM");
    writer.EndArray();
    writer.EndObject();

    const char *result = sb.GetString();
    ASSERT_TRUE(strstr(result, "\"name\"") != NULL);
    ASSERT_TRUE(strstr(result, "\"RapidJSON\"") != NULL);
    ASSERT_TRUE(strstr(result, "\"SAX\"") != NULL);
    ASSERT_TRUE(strstr(result, "\"DOM\"") != NULL);
}

// Test 4: Nested object access
static void test_nested_object() {
    TEST("nested_object");
    const char *json = "{\"level1\":{\"level2\":{\"value\":42}}}";
    rapidjson::Document doc;
    doc.Parse(json);
    ASSERT_FALSE(doc.HasParseError());

    const rapidjson::Value &l1 = doc["level1"];
    ASSERT_TRUE(l1.IsObject());
    const rapidjson::Value &l2 = l1["level2"];
    ASSERT_TRUE(l2.IsObject());
    ASSERT_EQ(l2["value"].GetInt(), 42);
}

// Test 5: Copy and move semantics
static void test_copy_move() {
    TEST("copy_move");
    rapidjson::Document doc;
    doc.SetObject();
    rapidjson::Value key("test", doc.GetAllocator());
    rapidjson::Value val(99);
    doc.AddMember(key, val, doc.GetAllocator());

    // Copy
    rapidjson::Document copy;
    copy.CopyFrom(doc, copy.GetAllocator());
    ASSERT_TRUE(copy.HasMember("test"));
    ASSERT_EQ(copy["test"].GetInt(), 99);

    // Move
    rapidjson::Document moved;
    moved = std::move(doc);
    ASSERT_TRUE(moved.HasMember("test"));
    ASSERT_EQ(moved["test"].GetInt(), 99);
}

int main() {
    test_parse_object();
    test_parse_array();
    test_write_json();
    test_nested_object();
    test_copy_move();

    if (failures > 0) {
        fprintf(stderr, "FAILED: %d test(s) failed\n", failures);
        printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"test_rapidjson\",\"discovered\":5,\"passedCount\":0}\n");
        return 1;
    }
    printf("OK: all 5 tests passed\n");
    printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"test_rapidjson\",\"discovered\":5,\"passedCount\":5}\n");
    return 0;
}