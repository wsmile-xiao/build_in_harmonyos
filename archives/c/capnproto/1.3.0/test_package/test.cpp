// test_capnproto.cpp — smoke test for capnproto 1.3.0 Conan package.
// Verifies KJ utility library and Cap'n Proto headers compile and link,
// and exercises a real serialization roundtrip (not a stub).

#include <capnp/message.h>
#include <capnp/serialize.h>
#include <kj/array.h>
#include <kj/string.h>
#include <kj/debug.h>
#include <cstdio>
#include <cstring>

static int tests_passed = 0;
static int tests_total = 0;

#define CHECK(cond, msg) do { \
    tests_total++; \
    if (!(cond)) { fprintf(stderr, "FAIL: %s\n", msg); return 1; } \
    printf("  %s: OK\n", msg); tests_passed++; \
} while(0)

int main() {
    // 1. KJ heapArray allocation
    {
        auto arr = kj::heapArray<char>(64);
        memset(arr.begin(), 0xAB, arr.size());
        CHECK(arr[0] == (char)0xAB && arr[63] == (char)0xAB,
              "kj::heapArray alloc and memset");
    }

    // 2. KJ string formatting
    {
        auto s = kj::str("capnproto-", 1, ".", 3, ".", 0);
        CHECK(s == kj::StringPtr("capnproto-1.3.0"),
              "kj::str formatting");
    }

    // 3. KJ ArrayPtr slice
    {
        kj::byte data[] = {1, 2, 3, 4, 5};
        auto ptr = kj::arrayPtr(data, 5);
        CHECK(ptr.size() == 5 && ptr[0] == 1 && ptr[4] == 5,
              "kj::arrayPtr byte access");
    }

    // 4. Real Cap'n Proto serialization roundtrip: write a list root,
    //    flatten to a word array, read it back and verify contents.
    {
        capnp::MallocMessageBuilder builder;
        auto root = builder.initRoot<capnp::List<uint32_t>>(3);
        root.set(0, 0xCA11);
        root.set(1, 0xDEC0);
        root.set(2, 0xFEED);

        kj::Array<capnp::word> words = capnp::messageToFlatArray(builder);
        capnp::FlatArrayMessageReader reader(words);
        auto check = reader.getRoot<capnp::List<uint32_t>>();
        CHECK(check.size() == 3 &&
              check[0] == 0xCA11 && check[1] == 0xDEC0 && check[2] == 0xFEED,
              "capnp list serialization roundtrip via messageToFlatArray");
    }

    printf("\ncapnproto 1.3.0 test_package: %d/%d PASSED\n",
           tests_passed, tests_total);
    return 0;
}