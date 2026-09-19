// test_gason.cpp — Conan L1 consumer test (消费者用例)
//
// Simulates an upper-layer business component consuming the gason library
// through its INSTALLED public interface only:
//   - public header  : gason.h  (installed under include/)
//   - public API     : jsonParse / JsonValue / JsonAllocator / JsonIterator
//   - link target    : libgason.a (installed under lib/)
//
// It parses a JSON document and verifies observable results (tags, numbers,
// strings, object/array iteration) — a real API call with checked output,
// not a print-only stub.
#include <gason.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failures = 0;

#define CHECK(cond, msg)                              \
    do {                                              \
        if (!(cond)) {                                \
            fprintf(stderr, "FAIL: %s\n", msg);       \
            ++failures;                               \
        }                                             \
    } while (0)

int main(void) {
    char source[] = "{\"name\":\"gason\",\"version\":1.0,\"tags\":[\"json\",\"parser\"],\"ok\":true,\"nothing\":null}";
    char *endptr;
    JsonValue value;
    JsonAllocator allocator;

    int status = jsonParse(source, &endptr, &value, allocator);
    CHECK(status == JSON_OK, "jsonParse returns JSON_OK");
    if (status != JSON_OK) {
        fprintf(stderr, "parse error %d at %zd: %s\n",
                status, endptr - source, jsonStrError(status));
        return 1;
    }

    // top-level must be an object
    CHECK(value.getTag() == JSON_OBJECT, "top-level tag is JSON_OBJECT");

    const char *name = nullptr;
    double version = 0.0;
    int tag_count = 0;
    bool ok_seen = false;
    bool null_seen = false;

    for (JsonNode *n : value) {
        if (strcmp(n->key, "name") == 0) {
            CHECK(n->value.getTag() == JSON_STRING, "name is a string");
            name = n->value.toString();
        } else if (strcmp(n->key, "version") == 0) {
            CHECK(n->value.getTag() == JSON_NUMBER, "version is a number");
            version = n->value.toNumber();
        } else if (strcmp(n->key, "tags") == 0) {
            CHECK(n->value.getTag() == JSON_ARRAY, "tags is an array");
            for (JsonNode *t : n->value) {
                CHECK(t->value.getTag() == JSON_STRING, "tag is a string");
                ++tag_count;
            }
        } else if (strcmp(n->key, "ok") == 0) {
            CHECK(n->value.getTag() == JSON_TRUE, "ok is JSON_TRUE");
            ok_seen = true;
        } else if (strcmp(n->key, "nothing") == 0) {
            CHECK(n->value.getTag() == JSON_NULL, "nothing is JSON_NULL");
            null_seen = true;
        }
    }

    CHECK(name != nullptr && strcmp(name, "gason") == 0, "name == \"gason\"");
    CHECK(version == 1.0, "version == 1.0");
    CHECK(tag_count == 2, "tags array has 2 entries");
    CHECK(ok_seen, "ok member present");
    CHECK(null_seen, "nothing member present");

    if (failures == 0) {
        printf("test_gason: ALL CHECKS PASSED (name=%s version=%.1f tags=%d)\n",
               name ? name : "", version, tag_count);
        return 0;
    }
    fprintf(stderr, "test_gason: %d CHECK(S) FAILED\n", failures);
    return 1;
}
