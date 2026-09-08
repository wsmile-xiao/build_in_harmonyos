// test_package/test_svector.cpp — consumer test for svector 1.4.0 (R34)
// Compiles against the packaged include/ankerl/svector.h and exercises the
// real API: inline (SVO) storage, heap growth, element access, erase and
// non-trivial element types. No assert(): the build may define NDEBUG.
#include <ankerl/svector.h>

#include <cstdio>
#include <string>

static int failures = 0;

#define CHECK(cond) \
    do { \
        if (!(cond)) { \
            std::printf("FAIL: %s\n", #cond); \
            ++failures; \
        } \
    } while (0)

int main() {
    // inline (SVO) capacity path
    ankerl::svector<int, 4> v;
    CHECK(v.empty());
    CHECK(v.size() == 0u);
    CHECK(v.capacity() >= 4u);
    v.push_back(7);
    CHECK(v.size() == 1u);
    CHECK(v[0] == 7);
    CHECK(v.front() == 7);
    CHECK(v.back() == 7);

    // heap growth beyond the inline capacity (v[0]==7 already, so index k>0
    // holds k-1 after pushing 0..99)
    for (int i = 0; i < 100; ++i) {
        v.push_back(i);
    }
    CHECK(v.size() == 101u);
    CHECK(v[42] == 41);
    CHECK(v[100] == 99);

    // erase keeps order and shifts elements
    v.erase(v.begin() + 1);
    CHECK(v.size() == 100u);
    CHECK(v[1] == 1);

    // non-trivial element type with inline capacity 2
    ankerl::svector<std::string, 2> sv{"hello", "world"};
    CHECK(sv.size() == 2u);
    sv.push_back("svo");
    CHECK(sv.size() == 3u);
    CHECK(sv[0] == "hello");
    CHECK(sv[2] == "svo");

    if (failures != 0) {
        std::printf("FAILED %d checks\n", failures);
        return 1;
    }
    std::printf("OK: all svector consumer checks passed\n");
    return 0;
}
