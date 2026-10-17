// z42: substantive libsword API test for sword/1.9.0 test_package (R34).
// Every CHECK calls real libsword APIs (SWVersion/SWBuf/VerseKey) and compares
// concrete content; any failure exits non-zero so both ctest and the direct
// self.run(...) in test()/conan test are rc-gated.
#include <cstdio>
#include <cstring>

#include <sword/defs.h>
#include <sword/swversion.h>
#include <sword/swbuf.h>
#include <sword/versekey.h>

static int failures = 0;
static int assertions = 0;   // 实际执行的 CHECK 条数（打印值不再硬编码）
#define CHECK(cond)                                                            \
    do {                                                                       \
        ++assertions;                                                          \
        if (!(cond)) {                                                         \
            std::fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__,       \
                         #cond);                                               \
            ++failures;                                                        \
        }                                                                      \
    } while (0)

int main() {
    // 1) library version identity comes from the built library itself
    const sword::SWVersion &cur = sword::SWVersion::currentVersion;
    CHECK(cur.major == 1);
    CHECK(cur.minor == 9);
    std::printf("libsword currentVersion = %s\n", cur.getText());

    sword::SWVersion v("1.9.0");
    CHECK(v.major == 1 && v.minor == 9 && v.minor2 == 0);
    CHECK(cur.compare(v) == 0); // package version == built library version
    CHECK(std::strcmp(v.getText(), "1.9.0") == 0);

    // 2) SWBuf: the library's core string type
    sword::SWBuf a("alpha");
    CHECK(a == "alpha");
    CHECK(a != "ALPHA");
    CHECK(a.compare("beta") < 0);
    a += "b";
    CHECK(std::strcmp(a.c_str(), "alphab") == 0);

    // 3) VerseKey: canonical key parsing & ordering — same standalone usage
    //    as upstream tests/cppunit/versekey_test.cpp (no modules/conf needed)
    sword::VerseKey k1("Luke 1:1");
    CHECK(k1.getChapter() == 1);
    CHECK(k1.getVerse() == 1);
    CHECK(std::strcmp(k1.getOSISBookName(), "Luke") == 0);

    sword::VerseKey k2("John 3:16");
    CHECK(k2.getChapter() == 3);
    CHECK(k2.getVerse() == 16);
    CHECK(std::strcmp(k2.getOSISBookName(), "John") == 0);

    CHECK(k1 < k2); // canonical book order: Luke before John

    if (failures) {
        std::fprintf(stderr, "sword test_package: %d assertion(s) FAILED\n",
                     failures);
        return 1;
    }
    std::printf("sword 1.9.0 test_package: all %d assertion groups passed\n", assertions);
    return 0;
}
