/* Consumer-side test for the picohttpparser Conan package (Conan L1 test).
 *
 * R34: every check below goes through the public API declared in
 * picohttpparser.h and is evaluated at run time against the packaged library,
 * so the test cannot pass if the package (header or libpicohttpparser.a) is
 * missing, stale or broken.
 */
#include <stddef.h>
#include <stdio.h>
#include <string.h>

#include "picohttpparser.h"

static int g_checks;
static int g_failures;

#define CHECK(cond)                                                         \
    do {                                                                    \
        ++g_checks;                                                         \
        if (!(cond)) {                                                      \
            ++g_failures;                                                   \
            fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); \
        }                                                                   \
    } while (0)

/* Compare a (pointer, length) pair coming from the parser against a C string. */
static int str_eq(const char *a, size_t alen, const char *b)
{
    size_t blen = strlen(b);
    return a != NULL && alen == blen && memcmp(a, b, alen) == 0;
}

static void test_packaged_version(void)
{
    CHECK(strcmp(PICOHTTPPARSER_VERSION, "1.4") == 0);
    CHECK(PICOHTTPPARSER_VERSION_MAJOR == 1);
    CHECK(PICOHTTPPARSER_VERSION_MINOR == 4);
}

static void test_parse_request(void)
{
    static const char req[] = "GET /index.html?a=1 HTTP/1.1\r\n"
                              "Host: example.com\r\n"
                              "User-Agent: picohttpparser-conan-test\r\n"
                              "\r\n";
    const char *method = NULL, *path = NULL;
    size_t method_len = 0, path_len = 0, num_headers = 8;
    int minor_version = -1;
    struct phr_header headers[8];
    int consumed;

    consumed = phr_parse_request(req, sizeof(req) - 1, &method, &method_len, &path, &path_len,
                                 &minor_version, headers, &num_headers, 0);
    CHECK(consumed == (int)(sizeof(req) - 1));
    CHECK(str_eq(method, method_len, "GET"));
    CHECK(str_eq(path, path_len, "/index.html?a=1"));
    CHECK(minor_version == 1);
    CHECK(num_headers == 2);
    CHECK(str_eq(headers[0].name, headers[0].name_len, "Host"));
    CHECK(str_eq(headers[0].value, headers[0].value_len, "example.com"));
    CHECK(str_eq(headers[1].name, headers[1].name_len, "User-Agent"));
    CHECK(str_eq(headers[1].value, headers[1].value_len, "picohttpparser-conan-test"));
}

static void test_partial_request(void)
{
    /* 12 bytes stop inside the request line, so the parser must ask for more. */
    static const char req[] = "GET / HTTP/1.1\r\nHost: example.com\r\n\r\n";
    const char *method = NULL, *path = NULL;
    size_t method_len = 0, path_len = 0, num_headers = 8;
    int minor_version = -1;
    struct phr_header headers[8];

    CHECK(phr_parse_request(req, 12, &method, &method_len, &path, &path_len, &minor_version,
                            headers, &num_headers, 0) == -2);
}

static void test_parse_response(void)
{
    static const char res[] = "HTTP/1.1 200 OK\r\nContent-Length: 5\r\n\r\n";
    int minor_version = -1, status = -1;
    const char *msg = NULL;
    size_t msg_len = 0, num_headers = 8;
    struct phr_header headers[8];
    int consumed;

    consumed = phr_parse_response(res, sizeof(res) - 1, &minor_version, &status, &msg, &msg_len,
                                  headers, &num_headers, 0);
    CHECK(consumed == (int)(sizeof(res) - 1));
    CHECK(minor_version == 1);
    CHECK(status == 200);
    CHECK(str_eq(msg, msg_len, "OK"));
    CHECK(num_headers == 1);
    CHECK(str_eq(headers[0].name, headers[0].name_len, "Content-Length"));
    CHECK(str_eq(headers[0].value, headers[0].value_len, "5"));
}

static void test_parse_headers(void)
{
    static const char hdrs[] = "X-Test: one\r\nX-Multi: two\r\n\r\n";
    size_t num_headers = 4;
    struct phr_header headers[4];
    int consumed;

    consumed = phr_parse_headers(hdrs, sizeof(hdrs) - 1, headers, &num_headers, 0);
    CHECK(consumed == (int)(sizeof(hdrs) - 1));
    CHECK(num_headers == 2);
    CHECK(str_eq(headers[0].name, headers[0].name_len, "X-Test"));
    CHECK(str_eq(headers[1].name, headers[1].name_len, "X-Multi"));
}

static void test_decode_chunked(void)
{
    static const char encoded[] = "5\r\nhello\r\n0\r\n\r\n";
    char buf[sizeof(encoded)];
    struct phr_chunked_decoder dec = {0};
    size_t bufsz = sizeof(encoded) - 1;
    ssize_t rest;

    memcpy(buf, encoded, sizeof(encoded));
    /* consume_trailer is left 0, so the trailing CRLF is reported as undecoded;
     * upstream test.c expects the same value 2 for that decoder setting. */
    rest = phr_decode_chunked(&dec, buf, &bufsz);
    CHECK(rest == 2);
    CHECK(bufsz == 5);
    CHECK(str_eq(buf, bufsz, "hello"));
    CHECK(phr_decode_chunked_is_in_data(&dec) == 0);
}

static void test_decode_chunked_consume_trailer(void)
{
    static const char encoded[] = "5\r\nhello\r\n0\r\n\r\n";
    char buf[sizeof(encoded)];
    struct phr_chunked_decoder dec = {0};
    size_t bufsz = sizeof(encoded) - 1;

    memcpy(buf, encoded, sizeof(encoded));
    dec.consume_trailer = 1;
    /* With the trailer consumed nothing is left undecoded. */
    CHECK(phr_decode_chunked(&dec, buf, &bufsz) == 0);
    CHECK(bufsz == 5);
    CHECK(str_eq(buf, bufsz, "hello"));
}

static void test_decode_chunked_partial(void)
{
    /* Chunk size line + 3 of the 5 payload bytes -> incomplete, partial data kept. */
    char buf[] = "5\r\nhel";
    struct phr_chunked_decoder dec = {0};
    size_t bufsz = sizeof(buf) - 1;

    CHECK(phr_decode_chunked(&dec, buf, &bufsz) == -2);
    CHECK(bufsz == 3);
    CHECK(str_eq(buf, bufsz, "hel"));
}

static void test_decode_chunked_bad_input(void)
{
    /* "zz" is not a valid chunk size -> hard error. */
    char buf[] = "zz\r\nhello\r\n0\r\n\r\n";
    struct phr_chunked_decoder dec = {0};
    size_t bufsz = sizeof(buf) - 1;

    CHECK(phr_decode_chunked(&dec, buf, &bufsz) == -1);
}

int main(void)
{
    test_packaged_version();
    test_parse_request();
    test_partial_request();
    test_parse_response();
    test_parse_headers();
    test_decode_chunked();
    test_decode_chunked_consume_trailer();
    test_decode_chunked_partial();
    test_decode_chunked_bad_input();

    printf("picohttpparser consumer test: %d checks, %d failures\n", g_checks, g_failures);
    return g_failures == 0 ? 0 : 1;
}
