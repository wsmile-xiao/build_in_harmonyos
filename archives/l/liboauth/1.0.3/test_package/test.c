#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <oauth.h>

static int check(const char *what, const char *got, const char *expect) {
    if (strcmp(got, expect) != 0) {
        fprintf(stderr, "FAIL %s: got '%s', expected '%s'\n", what, got, expect);
        return 1;
    }
    printf("ok   %s = '%s'\n", what, got);
    return 0;
}

int main(void) {
    int fails = 0;

    /* 1. base64 encode (RFC 4648) */
    fails += check("base64(Hello world!)",
                   oauth_encode_base64(12, (const unsigned char *)"Hello world!"),
                   "SGVsbG8gd29ybGQh");

    /* 2. URL escape */
    fails += check("url_escape(a b&c/d)",
                   oauth_url_escape("a b&c/d"),
                   "a%20b%26c%2Fd");

    /* 3. HMAC-SHA1 signature (HMAC-SHA1("key","hello"), base64) */
    fails += check("hmac_sha1(key, 'hello')",
                   oauth_sign_hmac_sha1("hello", "key"),
                   "s0zqxFFv8joUPmHXnQ+npPvl8mY=");

    /* 4. plaintext signature (returns the shared key per OAuth 1.0 spec) */
    fails += check("plaintext('a','b')",
                   oauth_sign_plaintext("a", "b"),
                   "b");

    /* 5. round-trip base64 decode */
    {
        unsigned char buf[64] = {0};
        int n = oauth_decode_base64(buf, "SGVsbG8gd29ybGQh");
        if (n != 12 || memcmp(buf, "Hello world!", 12) != 0) {
            fprintf(stderr, "FAIL base64 decode round-trip (n=%d)\n", n);
            fails++;
        } else {
            printf("ok   base64 decode round-trip = 'Hello world!'\n");
        }
    }

    if (fails == 0) {
        printf("ALL PASS: liboauth 1.0.3 test_package\n");
        return 0;
    }
    fprintf(stderr, "%d assertion(s) FAILED\n", fails);
    return 1;
}
