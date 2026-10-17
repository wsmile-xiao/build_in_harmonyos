/* Consumer test for the packaged libpiano static library.
 *
 * Exercises offline libpiano APIs only (no network, no credentials):
 * error-string table, list helpers, station lookup and handle
 * init/destroy with dummy partner keys (blowfish ciphers are opened
 * locally, no Pandora RPC is performed).
 */
#include <stdio.h>
#include <string.h>

#include <gcrypt.h>
#include <piano.h>

static int checks = 0;
static int passed = 0;

#define CHECK(cond, name) do { \
    checks++; \
    if (cond) { \
        passed++; \
        printf("PASS: %s\n", name); \
    } else { \
        printf("FAIL: %s\n", name); \
    } \
} while (0)

int main(void) {
    const char *ok_str = PianoErrorToStr(PIANO_RET_OK);
    const char *err_str = PianoErrorToStr(PIANO_RET_ERR);
    const char *gcry_str = PianoErrorToStr(PIANO_RET_GCRY_ERR);

    CHECK(ok_str != NULL, "PianoErrorToStr(OK) returns non-NULL");
    CHECK(err_str != NULL, "PianoErrorToStr(ERR) returns non-NULL");
    CHECK(gcry_str != NULL, "PianoErrorToStr(GCRY_ERR) returns non-NULL");
    CHECK(ok_str != NULL && strlen(ok_str) > 0,
          "PianoErrorToStr(OK) is non-empty");
    CHECK(err_str != NULL && strcmp(ok_str, err_str) != 0,
          "OK and ERR strings differ");

    CHECK(PianoListCount(NULL) == 0, "PianoListCount(NULL) == 0");
    CHECK(PianoFindStationById(NULL, "0") == NULL,
          "PianoFindStationById(NULL) == NULL");
    CHECK(PianoFindStationById(NULL, "") == NULL,
          "PianoFindStationById(NULL, empty) == NULL");

    /* libgcrypt must be initialized before PianoInit opens ciphers. */
    CHECK(gcry_check_version(GCRYPT_VERSION) != NULL,
          "gcry_check_version works");

    {
        PianoHandle_t ph;
        PianoReturn_t ret = PianoInit(&ph, "user", "password", "device",
                                      "0123456789abcdef",
                                      "fedcba9876543210");
        CHECK(ret == PIANO_RET_OK, "PianoInit returns OK offline");
        if (ret == PIANO_RET_OK) {
            CHECK(ph.partner.user != NULL &&
                  strcmp(ph.partner.user, "user") == 0,
                  "PianoInit stores partner user");
            CHECK(ph.stations == NULL,
                  "fresh handle has no stations");
            PianoDestroy(&ph);
            printf("PASS: PianoDestroy completes\n");
            passed++;
            checks++;
        }
    }

    /* Destroying an empty playlist must be a safe no-op. */
    PianoDestroyPlaylist(NULL);
    printf("PASS: PianoDestroyPlaylist(NULL) is safe\n");
    passed++;
    checks++;

    printf("libpiano consumer tests: %d/%d passed\n", passed, checks);
    return (passed == checks) ? 0 : 1;
}
