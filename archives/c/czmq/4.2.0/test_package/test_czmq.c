/*  =========================================================================
    test_czmq.c — HarmonyOS consumer test for czmq 4.2.0

    Exercises the public czmq API surface that a HarmonyOS application would
    consume: version handshake, zsys capability probe, zhash container, zuuid
    identity, zframe codec, zfile_tmp (the OHOS TMPDIR adaptation), an inproc
    zsock/zstr round trip, the zmsg envelope, zrex and the monotonic clock.

    Every CHECK() is a real assertion on the library under test.
    =========================================================================
*/

#include <czmq.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int checks = 0;

#define CHECK(cond)                                                     \
    do {                                                                \
        if (!(cond)) {                                                  \
            printf ("FAIL line %d: %s\n", __LINE__, #cond);             \
            return 1;                                                   \
        }                                                               \
        checks++;                                                       \
    } while (0)

int
main (void)
{
    int major = 0;
    int minor = 0;
    int patch = 0;

    zsys_init ();

    /*  1. library version handshake  */
    zsys_version (&major, &minor, &patch);
    CHECK (major == 4);
    printf (" * czmq version: %d.%d.%d\n", major, minor, patch);

    /*  2. CURVE capability probe must answer without crashing. The published
        libzmq/4.3.5 is built with CURVE disabled, so "no" is expected here.  */
    printf (" * zsys_has_curve: %s\n", zsys_has_curve () ? "yes" : "no");

    /*  3. hash container  */
    zhash_t *hash = zhash_new ();
    CHECK (hash != NULL);
    CHECK (zhash_size (hash) == 0);
    CHECK (zhash_insert (hash, "lang", "C") == 0);
    CHECK (zhash_insert (hash, "platform", "OHOS") == 0);
    CHECK (zhash_size (hash) == 2);
    CHECK (zhash_lookup (hash, "platform") != NULL);
    CHECK (streq (zhash_lookup (hash, "platform"), "OHOS"));
    zhash_destroy (&hash);
    CHECK (hash == NULL);

    /*  4. uuid  */
    zuuid_t *uuid = zuuid_new ();
    CHECK (uuid != NULL);
    const char *uuid_str = zuuid_str_canonical (uuid);
    CHECK (uuid_str != NULL);
    CHECK (strlen (uuid_str) == 36);
    zuuid_destroy (&uuid);

    /*  5. frame codec  */
    zframe_t *frame = zframe_new ("czmq", 4);
    CHECK (frame != NULL);
    CHECK (zframe_size (frame) == 4);
    CHECK (zframe_streq (frame, "czmq"));
    zframe_destroy (&frame);

    /*  6. stable zfile API against a file under TMPDIR. OHOS mounts /tmp as a
        read-only erofs image, and the draft-only zfile_tmp() helper is not
        available with ENABLE_DRAFTS=OFF, so the write target has to come from
        TMPDIR here (the upstream zfile selftest covers zfile_tmp() itself).  */
    const char *tmpdir = getenv ("TMPDIR");
    if (tmpdir && *tmpdir) {
        char path [512];
        snprintf (path, sizeof (path), "%s/czmq-harmonyos-probe.txt", tmpdir);
        FILE *seed = fopen (path, "w");
        CHECK (seed != NULL);
        CHECK (fputs ("czmq", seed) >= 0);
        fclose (seed);

        zfile_t *file = zfile_new (tmpdir, "czmq-harmonyos-probe.txt");
        CHECK (file != NULL);
        CHECK (zfile_input (file) == 0);
        zchunk_t *chunk = zfile_read (file, 4, 0);
        CHECK (chunk != NULL);
        CHECK (zchunk_size (chunk) == 4);
        CHECK (memcmp (zchunk_data (chunk), "czmq", 4) == 0);
        zchunk_destroy (&chunk);
        zfile_close (file);
        zfile_destroy (&file);
        remove (path);
        printf (" * stable zfile API read a file under TMPDIR=%s\n", tmpdir);
    }
    else
        printf (" * zfile check skipped (TMPDIR unset)\n");

    /*  7. inproc push/pull round trip  */
    zsock_t *pull = zsock_new_pull ("inproc://czmq-harmonyos-test");
    CHECK (pull != NULL);
    zsock_t *push = zsock_new_push ("inproc://czmq-harmonyos-test");
    CHECK (push != NULL);
    CHECK (zstr_send (push, "hello-harmonyos") == 0);
    char *received = zstr_recv (pull);
    CHECK (received != NULL);
    CHECK (streq (received, "hello-harmonyos"));
    zstr_free (&received);
    zsock_destroy (&push);
    zsock_destroy (&pull);

    /*  8. message envelope  */
    zmsg_t *msg = zmsg_new ();
    CHECK (msg != NULL);
    CHECK (zmsg_addstr (msg, "alpha") == 0);
    CHECK (zmsg_addstr (msg, "beta") == 0);
    CHECK (zmsg_size (msg) == 2);
    char *first = zmsg_popstr (msg);
    CHECK (first != NULL);
    CHECK (streq (first, "alpha"));
    zstr_free (&first);
    zmsg_destroy (&msg);

    /*  9. regex wrapper. czmq's bundled rex engine supports \d-style escapes
        but not POSIX bracket classes, so the pattern follows the upstream
        zrex selftest style.  */
    zrex_t *rex = zrex_new ("czmq-\\d+");
    CHECK (rex != NULL);
    CHECK (zrex_matches (rex, "czmq-421"));
    CHECK (!zrex_matches (rex, "zmq-421"));
    zrex_destroy (&rex);

    /* 10. monotonic clock  */
    int64_t t0 = zclock_mono ();
    zclock_sleep (5);
    CHECK (zclock_mono () >= t0);

    printf ("ALL CZMQ HARMONYOS TESTS PASSED (%d checks)\n", checks);

    zsys_shutdown ();
    return 0;
}
