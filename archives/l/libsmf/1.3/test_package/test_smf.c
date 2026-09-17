/* libsmf test_package: real SMF round-trip, not a version query (R34).
 * Exercises the public API end to end:
 * smf_new -> smf_track_new -> smf_add_track -> smf_event_new_from_bytes
 * -> smf_track_add_event_seconds -> smf_save -> smf_delete -> smf_load
 * -> smf_decode, asserting each step. 8 checks total; every PASS line is
 * counted in HMBS_TEST_PACKAGE_RESULT discovered/passedCount.
 */
#include <smf.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(n, cond, label)                                              \
    do {                                                                   \
        if (!(cond)) {                                                     \
            fprintf(stderr, "FAIL %d: %s\n", (n), (label));                \
            return 1;                                                      \
        }                                                                  \
        printf("PASS %d: %s\n", (n), (label));                             \
    } while (0)

int main(void) {
    const char *ver = smf_get_version();
    CHECK(1, ver != NULL && ver[0] != '\0', "smf_get_version non-empty");

    smf_t *smf = smf_new();
    CHECK(2, smf != NULL, "smf_new");

    smf_track_t *track = smf_track_new();
    CHECK(3, track != NULL, "smf_track_new");

    smf_add_track(smf, track);
    CHECK(4, smf->number_of_tracks == 1, "smf_add_track count==1");

    /* Note-On, channel 0, middle C, velocity 100. */
    smf_event_t *ev = smf_event_new_from_bytes(0x90, 60, 100);
    CHECK(5, ev != NULL && smf_event_is_valid(ev), "event new_from_bytes+valid");

    smf_track_add_event_seconds(track, ev, 1.0);
    CHECK(6, track->number_of_events >= 1, "track_add_event_seconds");

    const char *path = "hmbs_libsmf_test.mid";
    int rc = smf_save(smf, path);
    CHECK(7, rc == 0, "smf_save to hmbs_libsmf_test.mid");
    smf_delete(smf);

    smf_t *smf2 = smf_load(path);
    CHECK(8, smf2 != NULL && smf2->number_of_tracks == 1, "smf_load roundtrip tracks==1");

    char *dump = smf_decode(smf2);
    if (dump != NULL) {
        printf("decoded song: %s\n", dump);
        free(dump);
    }
    smf_delete(smf2);

    printf("libsmf %s roundtrip OK\n", ver);
    return 0;
}
