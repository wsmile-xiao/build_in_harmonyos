// Consumer test for metaproxy: links the packaged static libmetaproxy as a
// library user would and drives real public APIs from
// <metaproxy/util.hpp>: database_name_normalize (lower-cases database
// names), memcmp2 (length-aware buffer comparison) and the header-only
// to_string helper. Every check compares against the semantics implemented
// in src/util.cpp; any mismatch exits non-zero.
#include <metaproxy/util.hpp>

#include <cstring>
#include <iostream>
#include <string>

static int failures = 0;

static void check_str(const char *name, const std::string &got,
                      const char *expected)
{
    if (got != expected)
    {
        std::cerr << name << ": got '" << got << "' expected '" << expected
                  << "'\n";
        ++failures;
    }
}

static void check_int(const char *name, int got, int expected)
{
    if (got != expected)
    {
        std::cerr << name << ": got " << got << " expected " << expected
                  << "\n";
        ++failures;
    }
}

int main()
{
    // 1. database_name_normalize: ASCII upper case folds to lower case.
    check_str("normalize-mixed",
              metaproxy_1::util::database_name_normalize("Default"), "default");
    check_str("normalize-upper",
              metaproxy_1::util::database_name_normalize("ABCDEF"), "abcdef");
    check_str("normalize-lower",
              metaproxy_1::util::database_name_normalize("alreadylower"),
              "alreadylower");

    // 2. memcmp2: 0 when equal, sign of the difference otherwise,
    // with the longer buffer winning on a common prefix.
    check_int("memcmp2-equal",
              metaproxy_1::util::memcmp2("abc", 3, "abc", 3), 0);
    check_int("memcmp2-less",
              metaproxy_1::util::memcmp2("a", 1, "b", 1), -1);
    check_int("memcmp2-greater",
              metaproxy_1::util::memcmp2("b", 1, "a", 1), 1);
    check_int("memcmp2-prefix",
              metaproxy_1::util::memcmp2("ab", 2, "a", 1), 1);

    // 3. Header-only to_string helper round-trips an integer.
    check_str("to-string", metaproxy_1::util::to_string(12345), "12345");

    if (failures)
    {
        std::cerr << "consumer_test: " << failures << " assertion(s) failed\n";
        return 1;
    }
    std::cout << "consumer_test: metaproxy util APIs OK\n";
    return 0;
}
