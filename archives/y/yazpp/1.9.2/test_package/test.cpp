// Consumer test for yazpp: links the static libyazpp/libyaz as a library
// user would, drives the public Yaz_Z_Query API (Type-1 query parse, copy
// and print round-trip) and asserts on the rendered RPN output.
#include <yazpp/z-query.h>

#include <cstring>
#include <iostream>
#include <string>

using namespace yazpp_1;

static int failures = 0;

static void check(const char *name, const std::string &got,
                  const char *expected)
{
    if (got != expected)
    {
        std::cerr << name << ": got '" << got << "' expected '" << expected
                  << "'\n";
        ++failures;
    }
}

int main()
{
    // 1. Real API call: parse a Type-1 query, copy it, print it back.
    Yaz_Z_Query q;
    q = "@and a b";

    Yaz_Z_Query q2;
    q2 = q;

    char out[100];
    q2.print(out, sizeof(out) - 1);
    check("and-query", out, "RPN @attrset Bib-1 @and a b");

    // 2. Single-term query round-trip.
    Yaz_Z_Query q3;
    q3 = "x";
    char out2[100];
    q3.print(out2, sizeof(out2) - 1);
    check("term-query", out2, "RPN @attrset Bib-1 x");

    // 3. Empty query round-trip.
    Yaz_Z_Query q4;
    q4 = "";
    char out3[100];
    q4.print(out3, sizeof(out3) - 1);
    check("empty-query", out3, "");

    if (failures)
    {
        std::cerr << "consumer_test: " << failures << " assertion(s) failed\n";
        return 1;
    }
    std::cout << "consumer_test: yazpp query round-trips OK\n";
    return 0;
}
