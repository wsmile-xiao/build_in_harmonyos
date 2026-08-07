#include <errno.h>
#include <stdio.h>
#include <string.h>

#include <adns.h>

#define CHECK(condition, message) \
    do { \
        if (!(condition)) { \
            fprintf(stderr, "FAIL: %s\n", message); \
            return __LINE__; \
        } \
    } while (0)

int main(void)
{
    struct sockaddr_storage storage;
    socklen_t length = sizeof(storage);
    char text[ADNS_ADDR2TEXT_BUFLEN];
    int text_length = sizeof(text);
    int port = 0;
    char tiny[1];
    int tiny_length = sizeof(tiny);

    CHECK(adns_text2addr("127.0.0.1", 5353, 0,
                         (struct sockaddr *)&storage, &length) == 0,
          "IPv4 text converts to sockaddr");
    CHECK(storage.ss_family == AF_INET, "converted family is AF_INET");
    CHECK(adns_addr2text((struct sockaddr *)&storage, 0, text,
                         &text_length, &port) == 0,
          "sockaddr converts back to text");
    CHECK(strcmp(text, "127.0.0.1") == 0, "IPv4 roundtrip preserves address");
    CHECK(port == 5353, "IPv4 roundtrip preserves port");
    CHECK(adns_addr2text((struct sockaddr *)&storage, 0, tiny,
                         &tiny_length, NULL) == ENOSPC,
          "small output buffer is rejected");
    length = sizeof(storage);
    CHECK(adns_text2addr("not-an-address", 0, 0,
                         (struct sockaddr *)&storage, &length) == EINVAL,
          "invalid address text is rejected");
    CHECK(adns_strerror(adns_s_ok) != NULL, "status string is available");

    puts("PASS: adns address conversion and negative checks");
    return 0;
}
