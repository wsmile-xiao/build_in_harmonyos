// Consumer test for libaemu 0.1.2: exercises the real aemu-base
// StringFormat API. Each CHECK prints a deterministic line; the final
// TEST_PACKAGE_SUMMARY trailer is parsed by test_package/conanfile.py
// for HMBS_TEST_PACKAGE_RESULT. No stubs: every check calls into the
// built library and validates the returned value.
#include <cstdio>
#include <string>

#include "aemu/base/StringFormat.h"

static int g_passed = 0;
static int g_failed = 0;

#define CHECK(cond, label)                                             \
    do {                                                               \
        if (cond) {                                                    \
            ++g_passed;                                                \
            std::printf("CHECK %s: PASS\n", label);                    \
        } else {                                                       \
            ++g_failed;                                                \
            std::printf("CHECK %s: FAIL\n", label);                    \
        }                                                              \
    } while (0)

int main() {
    using android::base::StringAppendFormat;
    using android::base::StringAppendFormatRaw;
    using android::base::StringFormat;

    // 1-4: StringFormatRaw basics.
    CHECK(android::base::StringFormatRaw("%s", "hello") == "hello", "raw-string");
    CHECK(android::base::StringFormatRaw("%d", 42) == "42", "raw-decimal");
    CHECK(android::base::StringFormatRaw("%s-%d", "a", 7) == "a-7", "raw-mixed");
    CHECK(android::base::StringFormatRaw("") == "", "raw-empty");

    // 5-8: templated StringFormat, incl. std::string unpacking.
    CHECK(StringFormat("%s", std::string("world")) == "world", "tmpl-std-string");
    CHECK(StringFormat("n=%d", 123) == "n=123", "tmpl-int");
    CHECK(StringFormat("%s/%s", std::string("x"), "y") == "x/y", "tmpl-mixed");
    {
        std::string long_arg(64, 'a');
        std::string got = StringFormat("v=%s", long_arg);
        CHECK(got.size() == 66 && got.compare(2, 64, long_arg) == 0, "tmpl-long");
    }

    // 9-12: append variants mutate the target string.
    {
        std::string s = "pre:";
        StringAppendFormatRaw(&s, "%d", 9);
        CHECK(s == "pre:9", "append-raw");
    }
    {
        std::string s;
        StringAppendFormat(&s, "%s=%d", std::string("k"), 1);
        CHECK(s == "k=1", "append-tmpl");
    }
    {
        std::string s = "a";
        StringAppendFormat(&s, "%s", std::string("b"));
        StringAppendFormat(&s, "%s", std::string("c"));
        CHECK(s == "abc", "append-chain");
    }
    {
        std::string s;
        StringAppendFormatRaw(&s, "%s", "");
        CHECK(s == "", "append-empty");
    }

    std::printf(
        "TEST_PACKAGE_SUMMARY: passed=%d failed=%d total=%d\n",
        g_passed, g_failed, g_passed + g_failed);
    return g_failed == 0 ? 0 : 1;
}
