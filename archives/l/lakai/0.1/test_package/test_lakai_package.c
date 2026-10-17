/*
 * test_lakai_package.c — consumer-view test for the packaged lakai 0.1.
 *
 * Includes the installed <lakai.h>, links the packaged liblakai, and calls the
 * library API.  Compiled and run by test_package/conanfile.py test().
 *
 * Exit 0 on success, 1 on failure; prints "assertions=N failures=M".
 */
#include <stdio.h>
#include <string.h>

#include <lakai.h>

static int g_assertions = 0;
static int g_failures = 0;

static void check(int cond, const char *what)
{
    g_assertions++;
    if (cond)
    {
        printf("PASS: %s\n", what);
    }
    else
    {
        g_failures++;
        printf("FAIL: %s\n", what);
        fprintf(stderr, "FAIL: %s\n", what);
    }
}

int main(void)
{
    char src[] = "S2000#+-.";
    char akai[16];
    char back[16];
    char one[2];
    unsigned char v;
    int n = (int)strlen(src);

    printf("== lakai test_package consumer test ==\n");

    /* ascii -> akai -> ascii round-trip equals the input */
    memset(akai, 0, sizeof(akai));
    memset(back, 0, sizeof(back));
    lakai_asciitoakai(src, akai, n);
    lakai_akaitoascii(akai, back, n);
    check(memcmp(back, src, n) == 0, "ascii->akai->ascii round-trip equals input");

    /* specific ASCII -> Akai mappings */
    one[0] = '0'; one[1] = 0; v = 0xFF; lakai_asciitoakai(one, (char *)&v, 1);
    check(v == 0, "'0' -> 0");
    one[0] = '#'; one[1] = 0; v = 0xFF; lakai_asciitoakai(one, (char *)&v, 1);
    check(v == 37, "'#' -> 37");
    one[0] = '+'; one[1] = 0; v = 0xFF; lakai_asciitoakai(one, (char *)&v, 1);
    check(v == 38, "'+' -> 38");
    one[0] = '-'; one[1] = 0; v = 0xFF; lakai_asciitoakai(one, (char *)&v, 1);
    check(v == 39, "'-' -> 39");
    one[0] = '.'; one[1] = 0; v = 0xFF; lakai_asciitoakai(one, (char *)&v, 1);
    check(v == 40, "'.' -> 40");

    /* specific Akai -> ASCII mappings */
    {
        char s[1];
        char d[1];
        s[0] = 36; d[0] = 0; lakai_akaitoascii(s, d, 1);
        check(d[0] == 'Z', "36 -> 'Z'");
        s[0] = 40; d[0] = 0; lakai_akaitoascii(s, d, 1);
        check(d[0] == '.', "40 -> '.'");
    }

    /* init / open / close contract (offline parts) */
    lakai_init();
    check(lakai_close(0) == -1, "lakai_close(0) with no open device returns -1");
    check(lakai_open((char *)"/nonexistent/lakai-pkg-device") < 0,
          "lakai_open(nonexistent device) returns failure");

    printf("assertions=%d failures=%d\n", g_assertions, g_failures);
    return g_failures == 0 ? 0 : 1;
}
