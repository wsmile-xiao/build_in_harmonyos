#include <zt.h>
#include <stdio.h>
#include <string.h>

/* Consumer test: exercise the real libzt 0.3.1 API (R34) instead of a
 * print-only stub. Builds a small suite like the upstream README example
 * and runs it through zt_main(). */

static const char *greeting(void) {
    return "hello there";
}

static void test_smoke(zt_t t) {
    zt_check(t, ZT_TRUE(2 + 2 == 4));
    zt_check(t, ZT_CMP_INT(2 + 2, ==, 4));
    zt_check(t, ZT_CMP_CSTR(greeting(), ==, "hello there"));
}

static void test_pack_and_compare(zt_t t) {
    zt_value v = zt_pack_integer(42, "test_pack_and_compare");
    zt_check(t, ZT_CMP_INT(v.as.integer, ==, 42));
    zt_check(t, ZT_CMP_INT(strlen(greeting()), ==, 11));
    zt_check(t, ZT_CMP_INT(zt_pack_nothing().kind, ==, ZT_NOTHING));
}

static void test_suite(zt_visitor v) {
    ZT_VISIT_TEST_CASE(v, test_smoke);
    ZT_VISIT_TEST_CASE(v, test_pack_and_compare);
}

int main(int argc, char **argv, char **envp) {
    return zt_main(argc, argv, envp, test_suite);
}