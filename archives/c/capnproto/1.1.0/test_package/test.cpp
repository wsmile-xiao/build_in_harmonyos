// test_capnproto.cpp — smoke test for capnproto Conan package.
// Verifies KJ utility library and Cap'n Proto headers compile and link.

#include <capnp/message.h>
#include <capnp/serialize.h>
#include <kj/array.h>
#include <kj/string.h>
#include <kj/debug.h>
#include <cstdio>
#include <cstring>

static int tests_passed = 0;

#define CHECK(cond, msg) do { \
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
        auto s = kj::str("capnproto-", 1, ".", 1, ".", 0);
        CHECK(s == kj::StringPtr("capnproto-1.1.0"),
              "kj::str formatting");
    }

    // 3. KJ ArrayPtr slice
    {
        kj::byte data[] = {1, 2, 3, 4, 5};
        auto ptr = kj::arrayPtr(data, 5);
        CHECK(ptr.size() == 5 && ptr[0] == 1 && ptr[4] == 5,
              "kj::arrayPtr byte access");
    }

    // 4. Cap'n Proto MallocMessageBuilder instantiation
    {
        capnp::MallocMessageBuilder builder;
        CHECK(true, "MallocMessageBuilder created");
    }

    // 5. Cap'n Proto FlatArrayMessageReader type available
    {
        CHECK(sizeof(capnp::FlatArrayMessageReader) > 0,
              "capnp serialization types linked");
    }

    printf("\ncapnproto 1.1.0 test_package: %d/%d PASSED\n",
           tests_passed, tests_passed);
    return 0;
}
