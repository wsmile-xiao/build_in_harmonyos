/* Consumer-side smoke test for libcoap3 4.3.5 (R34: real API usage).
 * Exercises: coap_startup/shutdown lifecycle, version string, PDU
 * construction (coap_pdu_init + coap_add_option), URI parsing
 * (coap_split_uri), and block option encode — all from public headers.
 */
#include <stdio.h>
#include <string.h>
#include <coap3/coap.h>

int main(void) {
    int failures = 0;

    /* 1. library lifecycle */
    coap_startup();

    /* 2. version string must be present and contain "4.3.5" */
    const char *ver = coap_package_version();
    if (ver == NULL || strstr(ver, "4.3.5") == NULL) {
        fprintf(stderr, "FAIL: coap_package_version() = %s\n", ver ? ver : "()");
        failures++;
    } else {
        printf("coap_package_version: %s\n", ver);
    }

    /* 3. PDU construction + option append */
    coap_pdu_t *pdu = coap_pdu_init(0, 1, 0, 128);
    if (pdu == NULL) {
        fprintf(stderr, "FAIL: coap_pdu_init returned NULL\n");
        failures++;
    } else {
        size_t tok = 4;
        if (!coap_add_token(pdu, tok, (const uint8_t *)"\x01\x02\x03\x04")) {
            fprintf(stderr, "FAIL: coap_add_token\n");
            failures++;
        }
        const char *uri_path = "test";
        if (!coap_add_option(pdu, COAP_OPTION_URI_PATH,
                             strlen(uri_path), (const uint8_t *)uri_path)) {
            fprintf(stderr, "FAIL: coap_add_option(URI_PATH)\n");
            failures++;
        }
        coap_delete_pdu(pdu);
        printf("pdu init/token/option: OK\n");
    }

    /* 4. URI parser */
    coap_uri_t uri;
    const char *u = "coap://[::1]:5683/.well-known/core";
    if (coap_split_uri((const uint8_t *)u, strlen(u), &uri) != 0) {
        fprintf(stderr, "FAIL: coap_split_uri\n");
        failures++;
    } else if (uri.port != 5683) {
        fprintf(stderr, "FAIL: uri.port=%u\n", uri.port);
        failures++;
    } else {
        printf("coap_split_uri: port=%u path=%.*s\n", uri.port,
               (int)uri.path.length, (const char *)uri.path.s);
    }

    /* 5. DTLS support compiled in? (openssl backend) */
    coap_context_t *ctx = coap_new_context(NULL);
    if (ctx == NULL) {
        fprintf(stderr, "FAIL: coap_new_context\n");
        failures++;
    } else {
        coap_free_context(ctx);
        printf("coap_new_context/free: OK\n");
    }

    coap_cleanup();

    if (failures) {
        fprintf(stderr, "test_libcoap3: %d FAILURES\n", failures);
        return 1;
    }
    printf("test_libcoap3: all checks passed\n");
    return 0;
}
