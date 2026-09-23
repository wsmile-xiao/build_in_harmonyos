#include <socket99.h>

#include <netinet/in.h>
#include <stdio.h>
#include <string.h>

static int failures;

#define CHECK(condition, message) \
    do { \
        if (!(condition)) { \
            fprintf(stderr, "FAIL: %s\n", message); \
            failures++; \
        } \
    } while (0)

int main(void) {
    socket99_config cfg = {
        .IPv4 = "127.0.0.1",
        .datagram = true,
    };
    struct addrinfo hints;
    socket99_set_hints(&cfg, &hints);

    CHECK(hints.ai_family == AF_INET, "IPv4 selects AF_INET");
    CHECK(hints.ai_socktype == SOCK_DGRAM, "datagram selects SOCK_DGRAM");
    CHECK((hints.ai_flags & AI_NUMERICHOST) != 0,
          "literal IPv4 selects AI_NUMERICHOST");
    CHECK((hints.ai_flags & AI_PASSIVE) == 0,
          "UDP client does not select AI_PASSIVE");

    socket99_config invalid = {
        .IPv4 = "127.0.0.1",
        .IPv6 = "::1",
    };
    socket99_result result;
    CHECK(!socket99_open(&invalid, &result),
          "contradictory address families are rejected");
    CHECK(result.status == SOCKET99_ERROR_CONFIGURATION,
          "configuration error status is reported");

    char message[128];
    int message_length = socket99_snprintf(message, sizeof(message), &result);
    CHECK(message_length > 0, "socket99_snprintf returns message length");
    CHECK(strstr(message, "configuration") != NULL,
          "formatted error names the configuration failure");

    if (failures != 0) {
        return 1;
    }
    puts("socket99 consumer checks: 8 passed");
    return 0;
}
