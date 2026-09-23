#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "mpdecimal.h"
#include "decimal.hh"

/* 消费者验证: 实质调用 mpdecimal (C) 与 libmpdec++ (C++) API (R34) */
static int test_c_api(void) {
    mpd_context_t ctx;
    mpd_t *a, *b, *result;
    char *s;

    mpd_defaultcontext(&ctx);
    a = mpd_new(&ctx);
    b = mpd_new(&ctx);
    result = mpd_new(&ctx);
    if (!a || !b || !result) return 1;

    mpd_set_string(a, "1.5", &ctx);
    mpd_set_string(b, "2.25", &ctx);
    mpd_add(result, a, b, &ctx);

    s = mpd_to_sci(result, 1);
    if (!s) { mpd_del(a); mpd_del(b); mpd_del(result); return 1; }
    printf("C API: 1.5 + 2.25 = %s\n", s);
    /* expect 3.75 */
    int ok = (strncmp(s, "3.75", 4) == 0);
    mpd_free(s);
    mpd_del(a); mpd_del(b); mpd_del(result);
    return ok ? 0 : 1;
}

static int test_cpp_api(void) {
    decimal::Decimal a("3.5"), b("2.5");
    decimal::Decimal c = a + b;
    std::string s = c.repr();
    printf("C++ API: 3.5 + 2.5 = %s\n", s.c_str());
    return (s.find("6.0") != std::string::npos) ? 0 : 1;
}

int main(void) {
    printf("mpdecimal %s consumer test\n", mpd_version());
    if (test_c_api() != 0) {
        printf("C API test FAILED\n");
        return 1;
    }
    if (test_cpp_api() != 0) {
        printf("C++ API test FAILED\n");
        return 1;
    }
    printf("ALL OK\n");
    return 0;
}