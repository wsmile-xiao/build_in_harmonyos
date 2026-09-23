#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libcanlock-3/canlock-hp.h>
#include <libcanlock-3/canlock.h>

#define CHECK(condition, message) \
    do { \
        if (!(condition)) { \
            fprintf(stderr, "FAIL: %s\n", message); \
            return __LINE__; \
        } \
    } while (0)

int main(void)
{
    static const unsigned char secret[] = "ExampleSecret";
    static const unsigned char message_id[] = "<12345@mid.example>";
    static const char expected_key[] =
        "sha256:qv1VXHYiCGjkX/N1nhfYKcAeUn8bCVhrWhoKuBSnpMA=";
    static const char expected_lock[] =
        "sha256:s/pmK/3grrz++29ce2/mQydzJuc7iqHn1nqcJiQTPMc=";
    static const char expected_parsed[] =
        "sha256:s/pmK/3grrz++29ce2/mQydzJuc7iqHn1nqcJiQTPMc= "
        "sha1:nonsense";
    static const char field[] =
        "Cancel-Lock: (comment) sha256:s/pmK/3grrz++29ce2/"
        "mQydzJuc7iqHn1nqcJiQTPMc= sha1:nonsense";
    char *key;
    char *lock;
    char *parsed;

    CHECK(CL_API_MAJOR == 3 && CL_API_MINOR == 3,
          "public API version is 3.3");

    key = cl_get_key(CL_SHA256, secret, sizeof(secret) - 1,
                     message_id, sizeof(message_id) - 1);
    lock = cl_get_lock(CL_SHA256, secret, sizeof(secret) - 1,
                       message_id, sizeof(message_id) - 1);
    CHECK(key != NULL, "Cancel-Key generation succeeds");
    CHECK(lock != NULL, "Cancel-Lock generation succeeds");
    CHECK(strcmp(key, expected_key) == 0,
          "Cancel-Key matches the RFC 8315 test vector");
    CHECK(strcmp(lock, expected_lock) == 0,
          "Cancel-Lock matches the RFC 8315 test vector");
    CHECK(cl_verify(CL_SHA256, key + 7, lock + 7) == 0,
          "generated key verifies against generated lock");
    CHECK(cl_verify(CL_SHA256, "invalid", lock + 7) != 0,
          "invalid key is rejected");

    parsed = cl_hp_parse_field(field, sizeof(field) - 1);
    CHECK(parsed != NULL, "installed header parser is executable");
    CHECK(strcmp(parsed, expected_parsed) == 0,
          "header parser extracts and normalizes all syntactic locks");

    free(parsed);
    free(lock);
    free(key);
    puts("PASS: canlock core and header-parser APIs");
    return 0;
}
