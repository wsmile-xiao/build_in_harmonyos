/*
 * dnswire test_package — Conan L1 test.
 *
 * Uses the INSTALLED package only (public headers dnswire/*.h, public API):
 * builds a dnstap event, encodes it to protobuf with dnstap_encode_protobuf(),
 * decodes it back with dnstap_decode_protobuf(), and verifies the round trip.
 * Not an empty shell: asserts actual API behavior and prints the result.
 */
#include <dnswire/dnswire.h>
#include <dnswire/dnstap.h>
#include <dnswire/version.h>

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failures = 0;
#define CHECK(cond, msg)                          \
    do {                                          \
        if (!(cond)) {                            \
            fprintf(stderr, "FAIL: %s\n", msg);   \
            failures++;                           \
        }                                         \
        else {                                    \
            printf("PASS: %s\n", msg);            \
        }                                         \
    } while (0)

int main(void)
{
    struct dnstap d = DNSTAP_INITIALIZER;
    static char identity[] = "conan-test-package";
    static unsigned char qaddr[4] = { 10, 0, 0, 1 };
    static unsigned char raddr[4] = { 9, 9, 9, 9 };

    dnstap_set_identity_string(d, identity);
    dnstap_set_version_string(d, DNSWIRE_VERSION_STRING);
    dnstap_set_type(d, DNSTAP_TYPE_MESSAGE);
    dnstap_message_set_type(d, DNSTAP_MESSAGE_TYPE_CLIENT_QUERY);
    dnstap_message_set_socket_family(d, DNSTAP_SOCKET_FAMILY_INET);
    dnstap_message_set_socket_protocol(d, DNSTAP_SOCKET_PROTOCOL_TCP);
    dnstap_message_set_query_address(d, qaddr, sizeof(qaddr));
    dnstap_message_set_query_port(d, 53);

    size_t need = dnstap_encode_protobuf_size(&d);
    CHECK(need > 0, "dnstap_encode_protobuf_size() > 0");
    uint8_t* buf = (uint8_t*)malloc(need ? need : 1);
    CHECK(buf != NULL, "buffer alloc");
    size_t wrote = dnstap_encode_protobuf(&d, buf);
    CHECK(wrote == need && wrote > 0, "dnstap_encode_protobuf() wrote data");

    struct dnstap d2 = DNSTAP_INITIALIZER;
    CHECK(dnstap_decode_protobuf(&d2, buf, wrote) == 0,
          "dnstap_decode_protobuf() ok");
    CHECK(dnstap_message_type(d2) == DNSTAP_MESSAGE_TYPE_CLIENT_QUERY,
          "decoded message type == CLIENT_QUERY");
    CHECK(dnstap_message_query_port(d2) == 53, "decoded query_port == 53");
    CHECK(dnstap_identity_length(d2) == strlen(identity) &&
              memcmp(dnstap_identity(d2), identity,
                     dnstap_identity_length(d2)) == 0,
          "decoded identity matches");

    dnstap_cleanup(&d2);
    dnstap_cleanup(&d);
    free(buf);

    printf("dnswire %s test_package: %s\n",
           DNSWIRE_VERSION_STRING, failures ? "FAILED" : "PASSED");
    return failures ? 1 : 0;
}