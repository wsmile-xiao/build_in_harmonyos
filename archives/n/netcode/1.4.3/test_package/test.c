/* Consumer test for the netcode Conan package (HarmonyOS PC adaptation).
 *
 * Exercises the real public API against the packaged library:
 * version macros, address parse/format/compare, default client/server
 * configs, and connect token generation (vendored sodium crypto path),
 * including the v1.4.3 runtime bound on num_server_addresses (#173).
 * Results are reported as TAP lines parsed by test_package/conanfile.py.
 */
#include <netcode.h>

#include <stdint.h>
#include <stdio.h>
#include <string.h>

static int s_assertions = 0;
static int s_failures = 0;

#define CHECK(cond)                                                          \
    do {                                                                     \
        s_assertions++;                                                      \
        if (!(cond)) {                                                       \
            s_failures++;                                                    \
            printf("# ASSERT FAILED %s:%d: %s\n", __FILE__, __LINE__, #cond); \
        }                                                                    \
    } while (0)

static void test_version(void)
{
    CHECK(NETCODE_VERSION_MAJOR == 1);
    CHECK(NETCODE_VERSION_MINOR == 4);
    CHECK(NETCODE_VERSION_PATCH == 3);
    CHECK(strcmp(NETCODE_VERSION_FULL, "1.4.3") == 0);
}

static void test_address(void)
{
    struct netcode_address_t address;
    struct netcode_address_t again;
    char buffer[256];

    CHECK(netcode_parse_address("127.0.0.1:40000", &address) == NETCODE_OK);
    CHECK(address.type == NETCODE_ADDRESS_IPV4);
    CHECK(address.port == 40000);
    CHECK(netcode_address_to_string(&address, buffer) != NULL);
    CHECK(netcode_parse_address(buffer, &again) == NETCODE_OK);
    CHECK(netcode_address_equal(&address, &again) == 1);
    CHECK(netcode_parse_address("[::1]:40001", &address) == NETCODE_OK);
    CHECK(address.type == NETCODE_ADDRESS_IPV6);
    CHECK(netcode_parse_address("not_an_address", &address) == NETCODE_ERROR);
}

static void test_config(void)
{
    struct netcode_client_config_t client_config;
    struct netcode_server_config_t server_config;

    netcode_default_client_config(&client_config);
    netcode_default_server_config(&server_config);
    netcode_log_level(NETCODE_LOG_LEVEL_DEBUG);
    netcode_log_level(NETCODE_LOG_LEVEL_ERROR);
    CHECK(1); /* reached: default configs + log level switch ran */
    CHECK(client_config.override_send_and_receive == 0);
}

static void test_connect_token(void)
{
    static const char * servers[] = { "127.0.0.1:40000" };
    uint8_t private_key[NETCODE_KEY_BYTES];
    uint8_t user_data[NETCODE_USER_DATA_BYTES];
    uint8_t connect_token[NETCODE_CONNECT_TOKEN_BYTES];
    int i;

    netcode_random_bytes(private_key, NETCODE_KEY_BYTES);
    for (i = 0; i < NETCODE_USER_DATA_BYTES; i++)
        user_data[i] = (uint8_t)i;

    CHECK(netcode_generate_connect_token(1, servers, servers,
                                         30, 10, 12345ULL, 0x1122334455667788ULL,
                                         private_key, user_data,
                                         connect_token) == NETCODE_OK);
    /* v1.4.3 fix: out-of-range counts fail at runtime, not just assert. */
    CHECK(netcode_generate_connect_token(NETCODE_MAX_SERVERS_PER_CONNECT + 1,
                                         servers, servers,
                                         30, 10, 1ULL, 1ULL,
                                         private_key, user_data,
                                         connect_token) == NETCODE_ERROR);
}

int main(void)
{
    int failures_before;

    netcode_init();

    printf("TAP version 13\n");
    printf("1..4\n");

    failures_before = s_failures;
    test_version();
    printf("%s 1 - version\n", s_failures == failures_before ? "ok" : "not ok");

    failures_before = s_failures;
    test_address();
    printf("%s 2 - address\n", s_failures == failures_before ? "ok" : "not ok");

    failures_before = s_failures;
    test_config();
    printf("%s 3 - config\n", s_failures == failures_before ? "ok" : "not ok");

    failures_before = s_failures;
    test_connect_token();
    printf("%s 4 - connect_token\n", s_failures == failures_before ? "ok" : "not ok");

    netcode_term();

    printf("# assertions: %d failures: %d\n", s_assertions, s_failures);
    if (s_failures == 0) {
        printf("netcode consumer test passed\n");
        return 0;
    }
    printf("netcode consumer test FAILED\n");
    return 1;
}
