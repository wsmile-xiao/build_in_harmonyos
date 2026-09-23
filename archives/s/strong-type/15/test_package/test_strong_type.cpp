// test_strong_type.cpp — Substantive consumer test for strong-type 15 (Conan L1).
// Verifies a downstream consumer can include the packaged strong_type headers
// and use the strong typedef API through real assertions, following the
// upstream usage patterns (one modifier family per strong type).
#include <strong_type/strong_type.hpp>

#include <cstdio>

using arith_t = strong::type<int, struct arith_tag, strong::arithmetic>;
using ord_t = strong::type<int, struct ord_tag, strong::ordered>;
using diff_t = strong::type<int, struct diff_tag, strong::difference>;
using inc_t = strong::type<int, struct inc_tag, strong::incrementable>;

int run() {
    int failures = 0;
    auto check = [&](bool ok, const char *label) {
        if (!ok) { std::fprintf(stderr, "FAIL: %s\n", label); ++failures; }
    };

    // 1) arithmetic: add, subtract, unary minus
    arith_t a{10};
    check((a + arith_t{5}).value_of() == 15, "arithmetic add");
    check((a - arith_t{4}).value_of() == 6, "arithmetic subtract");
    check((-a).value_of() == -10, "arithmetic unary minus");

    // 2) ordered
    ord_t o{3};
    check(o < ord_t{9}, "ordered less");
    check(o >= ord_t{3}, "ordered greater-equal");

    // 3) difference: subtraction between instances, += with difference
    diff_t d1{20};
    diff_t d2{8};
    auto delta = d1 - d2;
    check(delta.value_of() == 12, "difference subtract");
    diff_t d3{1};
    d3 += delta;
    check(d3.value_of() == 13, "difference plus-assign");

    // 4) incrementable
    inc_t i{7};
    ++i;
    check(i.value_of() == 8, "incrementable pre-increment");
    inc_t old = i++;
    check(old.value_of() == 8 && i.value_of() == 9, "incrementable post-increment");

    return failures;
}

int main() {
    const int failures = run();
    if (failures == 0) {
        std::printf("PASS: strong-type 15 头文件库链接和强类型 API 验证通过\n");
        return 0;
    }
    return 1;
}
