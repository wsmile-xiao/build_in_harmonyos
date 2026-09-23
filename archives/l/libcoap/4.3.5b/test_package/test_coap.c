/* Consumer test for libcoap 4.3.5b: exercises real coap-3 APIs.
 * 12 checks: startup/version, URI parse (split/scheme/port), context and
 * UDP client-session lifecycle, session-backed PDU create, header
 * type/code/mid, option add, option present.
 * Any stub binary or empty fixture fails instead of silently passing.
 * Note: the PDU is built with the session-based public constructor
 * coap_new_pdu(type, code, session) on a real loopback UDP session, so no
 * network traffic is sent and the test does not depend on coap_pdu_init().
 */
#include <stdio.h>
#include <string.h>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#else
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#endif

#include <coap3/coap.h>

static int checks_passed = 0;

#define CHECK(cond, label) do { \
    if (!(cond)) { \
        fprintf(stderr, "CHECK FAILED: %s (line %d)\n", label, __LINE__); \
        return 1; \
    } \
    checks_passed++; \
    printf("CHECK PASS: %s\n", label); \
} while (0)

int main(void) {
    coap_startup();

    /* 1. Library version is non-empty. */
    const char *ver = coap_package_version();
    CHECK(ver != NULL && ver[0] != '\0', "package version non-empty");
    printf("libcoap version: %s\n", ver);

    /* 2. Parse a CoAP URI into its components. */
    coap_uri_t uri;
    const char *uri_str = "coap://127.0.0.1:5683/test/path?q=1";
    CHECK(coap_split_uri((const uint8_t *)uri_str, strlen(uri_str), &uri) == 0,
          "split coap uri");
    CHECK(uri.scheme == COAP_URI_SCHEME_COAP, "uri scheme is coap");
    CHECK(uri.port == 5683, "uri port is 5683");

    /* 3. Context plus a loopback UDP client session (no packet is sent). */
    coap_context_t *ctx = coap_new_context(NULL);
    CHECK(ctx != NULL, "context created");

    coap_address_t dst;
    coap_address_init(&dst);
    dst.addr.sin.sin_family = AF_INET;
    dst.addr.sin.sin_port = htons(COAP_DEFAULT_PORT);
    dst.addr.sin.sin_addr.s_addr = htonl(INADDR_LOOPBACK);

    coap_session_t *session =
        coap_new_client_session(ctx, NULL, &dst, COAP_PROTO_UDP);
    CHECK(session != NULL, "client session created");

    /* 4. Session-backed confirmable GET PDU with deterministic header. */
    coap_pdu_t *pdu =
        coap_new_pdu(COAP_MESSAGE_CON, COAP_REQUEST_CODE_GET, session);
    CHECK(pdu != NULL, "pdu created");
    CHECK(coap_pdu_get_type(pdu) == COAP_MESSAGE_CON, "pdu type CON");
    CHECK(coap_pdu_get_code(pdu) == COAP_REQUEST_CODE_GET, "pdu code GET");
    coap_pdu_set_mid(pdu, 0x1234);
    CHECK(coap_pdu_get_mid(pdu) == 0x1234, "pdu mid set");

    /* 5. Add a Uri-Path option and confirm it is present. */
    const uint8_t path[] = "test";
    CHECK(coap_add_option(pdu, COAP_OPTION_URI_PATH,
                          sizeof(path) - 1, path) != 0,
          "add Uri-Path option");

    /* 6. Option round-trips through the PDU iterator. */
    coap_opt_iterator_t oi;
    coap_opt_t *opt = coap_check_option(pdu, COAP_OPTION_URI_PATH, &oi);
    CHECK(opt != NULL, "Uri-Path option present");

    coap_delete_pdu(pdu);
    coap_session_release(session);
    coap_free_context(ctx);
    coap_cleanup();

    if (checks_passed != 12) {
        fprintf(stderr, "expected 12 checks, ran %d\n", checks_passed);
        return 1;
    }
    printf("ALL %d CHECKS PASSED\n", checks_passed);
    return 0;
}
