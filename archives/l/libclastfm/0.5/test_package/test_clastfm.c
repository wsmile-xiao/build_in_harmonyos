#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "clastfm.h"

/*
 * Offline consumer smoke test for libclastfm.
 *
 * The upstream test suite (src/test.c) is a set of 5 integration tests against
 * the live Last.fm web service (ws.audioscrobbler.com) and requires a personal
 * API key/secret plus outbound network. Neither CI nor the HMBS preflight
 * environment has those credentials or outbound network, so the upstream tests
 * cannot be executed there (see MANIFEST.yml audit).
 *
 * This test exercises the library WITHOUT network: LASTFM_init("0","0") only
 * performs curl_global_init and allocates an opaque session struct; it does
 * not contact Last.fm. LASTFM_dinit tears it down. We additionally static-assert
 * that the public enum/struct symbols are visible from the installed header,
 * which verifies the Conan package shipped clastfm.h correctly and that the
 * consumer can link against libclastfm.
 */

static int symbols_visible(void) {
    /* Enum values must be present in the installed clastfm.h */
    int ok = 1;
    ok &= (LASTFM_STATUS_OK == 0);
    ok &= (LASTFM_PERIOD_7DAY == 0);
    ok &= (LASTFM_PERIOD_COUNT == 5);
    ok &= (LASTFM_IMAGE_OG == 0);
    ok &= (LASTFM_IMAGE_URL_OG == 7);
    ok &= (sizeof(LASTFM_ALBUM_INFO) > 0);
    ok &= (sizeof(LASTFM_ARTIST_INFO) > 0);
    ok &= (sizeof(LASTFM_TRACK_INFO) > 0);
    ok &= (sizeof(LFMList) > 0);
    return ok ? 0 : 1;
}

int main(void) {
    int failed = 0;

    /* Symbol visibility from the installed header (compile-time + link-time) */
    if (symbols_visible() != 0) {
        printf("[FAIL] public symbols not visible from clastfm.h\n");
        failed++;
    } else {
        printf("[PASS] public symbols visible from clastfm.h\n");
    }

    /* LASTFM_init with dummy key/secret — no network, only curl_global_init + malloc */
    LASTFM_SESSION *s = LASTFM_init("0", "0");
    if (s == NULL) {
        printf("[FAIL] LASTFM_init returned NULL\n");
        failed++;
    } else {
        printf("[PASS] LASTFM_init allocated session\n");
        /* LASTFM_dinit — teardown, no network */
        if (LASTFM_dinit(s) != 0) {
            printf("[FAIL] LASTFM_dinit returned non-zero\n");
            failed++;
        } else {
            printf("[PASS] LASTFM_dinit released session\n");
        }
    }

    return failed;
}
