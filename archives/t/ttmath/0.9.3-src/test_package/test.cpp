// Consumer test for ttmath 0.9.3-src
//
// Exercises real ttmath API: big unsigned/signed integer arithmetic,
// big floating point arithmetic, and the mathematical expression parser.
// The upstream test harness already covers UInt<1..9> extensively; this
// consumer test validates that the packaged headers link and work from a
// downstream project's perspective.
#include <ttmath/ttmath.h>
#include <cstdio>
#include <string>

// Type aliases keep template commas out of the macro arguments.
typedef ttmath::UInt<2> T_UInt2;
typedef ttmath::Int<2>  T_Int2;
typedef ttmath::Big<1, 2> T_Big;

static int g_checks = 0;
static int g_failed = 0;
#define TTM_CHECK(cond) do { ++g_checks; if (!(cond)) { ++g_failed; std::printf("FAIL: %s\n", #cond); } } while (0)

int main() {
    // 1) Big unsigned integer arithmetic (UInt<2> == 128-bit on 64-bit words)
    T_UInt2 a("4294967295");
    T_UInt2 b("1");
    T_UInt2 sum = a + b;
    TTM_CHECK(sum == T_UInt2("4294967296"));

    T_UInt2 many("18446744073709551615");
    TTM_CHECK(many > sum);
    TTM_CHECK((many - sum) == T_UInt2("18446744069414584319"));

    // 2) Big floating point arithmetic (Big<1,2>: 1 exp word, 2 mantissa words)
    T_Big x("0.5");
    T_Big y("0.25");
    T_Big r = x + y;
    TTM_CHECK(r == T_Big("0.75"));
    T_Big prod = x * y;
    TTM_CHECK(prod == T_Big("0.125"));

    // 3) Signed big integer (Int<2>)
    T_Int2 n("-12345678901234");
    TTM_CHECK(n.IsSign());
    TTM_CHECK(n.ToString() == "-12345678901234");
    T_Int2 neg_one("-1");
    T_Int2 plus_one("1");
    TTM_CHECK((plus_one * neg_one).IsSign());

    // 4) Mathematical expression parser
    ttmath::Parser<T_Big> parser;
    ttmath::ErrorCode err = parser.Parse("2 + 3 * 4");
    TTM_CHECK(err == ttmath::err_ok);
    if (err == ttmath::err_ok) {
        TTM_CHECK(parser.stack[0].value == T_Big("14"));
    }

    std::printf("ttmath test_package: %d checks, %d failed\n", g_checks, g_failed);
    return g_failed == 0 ? 0 : 1;
}
