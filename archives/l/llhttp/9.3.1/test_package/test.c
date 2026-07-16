/*
 * test_llhttp.c — Consumer test for llhttp 9.3.1
 *
 * Verifies that the llhttp package can be linked and its core API works on
 * OpenHarmony. Beyond a basic GET smoke test, this file explicitly exercises
 * the three areas that an earlier device-side probe (25 ad-hoc cases, see
 * notes.md / README.md history) had flagged as "failing" — PATCH method
 * recognition, error-reason retrieval, and pause/resume state handling — and
 * shows they are in fact supported by llhttp 9.3.1.
 *
 * R34: every case calls real llhttp API (llhttp_init / llhttp_execute /
 * llhttp_get_method / llhttp_finish / llhttp_resume ...).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <llhttp.h>

static int g_pass = 0;
static int g_fail = 0;

#define CHECK(cond, label)                                          \
    do {                                                            \
        if (cond) { printf("PASS: %s\n", label); g_pass++; }        \
        else { printf("FAIL: %s\n", label); g_fail++; }             \
    } while (0)

/* ---------- Test 1: basic GET request parsing (original coverage) ---------- */

static int t1_method_called = 0;
static int t1_url_called = 0;
static int t1_header_field_called = 0;
static int t1_header_value_called = 0;
static int t1_headers_complete_called = 0;
static int t1_message_complete_called = 0;

static int t1_on_method(llhttp_t *parser, const char *at, size_t length) {
    if (length == 3 && strncmp(at, "GET", 3) == 0) { t1_method_called = 1; return 0; }
    return -1;
}
static int t1_on_url(llhttp_t *parser, const char *at, size_t length) {
    if (length == 11 && strncmp(at, "/index.html", 11) == 0) { t1_url_called = 1; return 0; }
    return -1;
}
static int t1_on_header_field(llhttp_t *parser, const char *at, size_t length) { t1_header_field_called++; return 0; }
static int t1_on_header_value(llhttp_t *parser, const char *at, size_t length) { t1_header_value_called++; return 0; }
static int t1_on_headers_complete(llhttp_t *parser) { t1_headers_complete_called = 1; return 0; }
static int t1_on_message_complete(llhttp_t *parser) { t1_message_complete_called = 1; return 0; }

static void test_get_basic(void) {
    printf("\n-- Test 1: basic GET request parsing --\n");
    t1_method_called = t1_url_called = t1_header_field_called = t1_header_value_called = 0;
    t1_headers_complete_called = t1_message_complete_called = 0;

    llhttp_t parser;
    llhttp_settings_t settings;
    llhttp_settings_init(&settings);
    settings.on_method = t1_on_method;
    settings.on_url = t1_on_url;
    settings.on_header_field = t1_on_header_field;
    settings.on_header_value = t1_on_header_value;
    settings.on_headers_complete = t1_on_headers_complete;
    settings.on_message_complete = t1_on_message_complete;
    llhttp_init(&parser, HTTP_REQUEST, &settings);

    const char *request =
        "GET /index.html HTTP/1.1\r\n"
        "Host: example.com\r\n"
        "Connection: keep-alive\r\n"
        "\r\n";

    llhttp_errno_t r = llhttp_execute(&parser, request, strlen(request));
    CHECK(r == HPE_OK, "GET: llhttp_execute returns HPE_OK");
    CHECK(t1_method_called, "GET: on_method callback invoked (GET)");
    CHECK(t1_url_called, "GET: on_url callback invoked (/index.html)");
    CHECK(t1_header_field_called == 2, "GET: on_header_field called 2 times");
    CHECK(t1_header_value_called == 2, "GET: on_header_value called 2 times");
    CHECK(t1_headers_complete_called, "GET: on_headers_complete callback invoked");
    CHECK(t1_message_complete_called, "GET: on_message_complete callback invoked");
}

/* ---------- Test 2: PATCH method recognition ---------- */

static int t2_method_is_patch = 0;
static int t2_message_complete = 0;

static int t2_on_method(llhttp_t *parser, const char *at, size_t length) {
    if (length == 5 && strncmp(at, "PATCH", 5) == 0) t2_method_is_patch = 1;
    return 0;
}
static int t2_on_message_complete(llhttp_t *parser) { t2_message_complete = 1; return 0; }

static void test_patch_method(void) {
    printf("\n-- Test 2: PATCH method recognition --\n");
    t2_method_is_patch = 0;
    t2_message_complete = 0;

    llhttp_t parser;
    llhttp_settings_t settings;
    llhttp_settings_init(&settings);
    settings.on_method = t2_on_method;
    settings.on_message_complete = t2_on_message_complete;
    llhttp_init(&parser, HTTP_REQUEST, &settings);

    const char *request =
        "PATCH /items/42 HTTP/1.1\r\n"
        "Host: api.example.com\r\n"
        "Content-Length: 0\r\n"
        "\r\n";

    llhttp_errno_t r = llhttp_execute(&parser, request, strlen(request));
    CHECK(r == HPE_OK, "PATCH: llhttp_execute returns HPE_OK");
    CHECK(t2_method_is_patch, "PATCH: on_method callback received \"PATCH\"");
    CHECK(llhttp_get_method(&parser) == HTTP_PATCH, "PATCH: llhttp_get_method == HTTP_PATCH");
    CHECK(strcmp(llhttp_method_name(HTTP_PATCH), "PATCH") == 0, "PATCH: llhttp_method_name(HTTP_PATCH) == \"PATCH\"");
    CHECK(t2_message_complete, "PATCH: message completed");
}

/* ---------- Test 3: error reason retrieval ---------- */

static void test_error_reason(void) {
    printf("\n-- Test 3: error reason retrieval --\n");

    llhttp_t parser;
    llhttp_settings_t settings;
    llhttp_settings_init(&settings);
    llhttp_init(&parser, HTTP_REQUEST, &settings);

    /* "GETX" matches the GET prefix but the 4th char is not a space, so the
     * method state machine rejects it. execute() sets the errno on the parser. */
    const char *bad = "GETX /bad HTTP/1.1\r\nHost: example.com\r\n\r\n";
    llhttp_errno_t r = llhttp_execute(&parser, bad, strlen(bad));

    CHECK(r != HPE_OK, "error: malformed method yields a parse error");
    CHECK(llhttp_get_errno(&parser) == r, "error: llhttp_get_errno matches the parse error");
    const char *reason = llhttp_get_error_reason(&parser);
    CHECK(reason != NULL, "error: llhttp_get_error_reason != NULL");
    CHECK(reason != NULL && reason[0] != '\0', "error: reason string is non-empty");
}

/* ---------- Test 4: pause / resume state handling ---------- */

static int t4_pause_first = 1;   /* pause only on the first on_message_begin */
static int t4_message_complete = 0;

static int t4_on_message_begin(llhttp_t *parser) {
    if (t4_pause_first) { t4_pause_first = 0; return HPE_PAUSED; }
    return 0;
}
static int t4_on_message_complete(llhttp_t *parser) { t4_message_complete = 1; return 0; }

static void test_pause_resume(void) {
    printf("\n-- Test 4: pause / resume state handling --\n");
    t4_pause_first = 1;
    t4_message_complete = 0;

    llhttp_t parser;
    llhttp_settings_t settings;
    llhttp_settings_init(&settings);
    settings.on_message_begin = t4_on_message_begin;
    settings.on_message_complete = t4_on_message_complete;
    llhttp_init(&parser, HTTP_REQUEST, &settings);

    const char *request =
        "GET /stream HTTP/1.1\r\n"
        "Host: example.com\r\n"
        "\r\n";
    size_t len = strlen(request);

    llhttp_errno_t r1 = llhttp_execute(&parser, request, len);
    CHECK(r1 == HPE_PAUSED, "pause: execute returns HPE_PAUSED after on_message_begin");
    CHECK(llhttp_get_errno(&parser) == HPE_PAUSED, "pause: llhttp_get_errno == HPE_PAUSED");

    const char *pos = llhttp_get_error_pos(&parser);
    int pos_ok = (pos != NULL && pos >= request && pos <= request + len);
    CHECK(pos_ok, "pause: llhttp_get_error_pos is valid");

    /* CHECK only records a failure and keeps going, but the resume path below
     * does pointer arithmetic on pos and hands it to llhttp_execute(). Bail out
     * so an invalid pos can never reach them. */
    if (!pos_ok) {
        CHECK(0, "pause: resume + continue returns HPE_OK");
        CHECK(0, "pause: message completed after resume");
        return;
    }

    /* Resume and feed the remaining (unconsumed) bytes; parsing must finish. */
    llhttp_resume(&parser);
    size_t consumed = (size_t)(pos - request);
    llhttp_errno_t r2 = llhttp_execute(&parser, pos, len - consumed);
    CHECK(r2 == HPE_OK, "pause: resume + continue returns HPE_OK");
    CHECK(t4_message_complete, "pause: message completed after resume");
}

int main(void) {
    test_get_basic();
    test_patch_method();
    test_error_reason();
    test_pause_resume();

    printf("\n==== Test Summary: %d passed, %d failed ====\n", g_pass, g_fail);
    if (g_fail) {
        printf("=== TEST FAILED ===\n");
        return 1;
    }
    printf("=== ALL TESTS PASSED ===\n");
    return 0;
}
