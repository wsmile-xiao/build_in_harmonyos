/* Consumer test for the installed libnjb package.
 *
 * The device facing API needs a Nomad Jukebox over libusb, but the songid tag
 * structures are pure in-memory objects, so they can be exercised anywhere.
 * NJB_Set_Debug()/NJB_Set_Unicode() are process wide setters without getters
 * and are only checked for not crashing.
 */
#include <stdio.h>
#include <string.h>

#include <libnjb.h>

static int checks;
static int failures;

static void check(int condition, const char *what)
{
    checks++;
    if (condition) {
        printf("ok   %s\n", what);
    } else {
        failures++;
        printf("FAIL %s\n", what);
    }
}

int main(void)
{
    njb_songid_t *song;
    njb_songid_frame_t *frame;
    njb_songid_frame_t *found;

    setvbuf(stdout, NULL, _IOLBF, 0);

    NJB_Set_Debug(1);
    NJB_Set_Unicode(1);
    check(1, "debug and unicode setters are callable");

    song = NJB_Songid_New();
    check(song != NULL, "NJB_Songid_New allocates a songid");
    if (song == NULL) {
        printf("checks: %d, failures: %d\n", checks, failures);
        return 1;
    }

    check(NJB_Songid_Getframe(song) == NULL,
          "a new songid has no frame to iterate");

    frame = NJB_Songid_Frame_New_String("Title", "Conan consumer");
    check(frame != NULL, "NJB_Songid_Frame_New_String creates a string frame");

    NJB_Songid_Addframe(song, frame);
    check(NJB_Songid_Getframe(song) == frame,
          "the added frame is returned by the iterator");

    found = NJB_Songid_Findframe(song, "Title");
    check(found == frame, "NJB_Songid_Findframe finds the frame by label");
    check(NJB_Songid_Findframe(song, "Missing") == NULL,
          "NJB_Songid_Findframe returns NULL for an unknown label");

    NJB_Songid_Reset_Getframe(song);
    check(NJB_Songid_Getframe(song) == frame,
          "reset restarts the frame iteration");

    frame = NJB_Songid_Frame_New_String("Artist", "OpenHarmony");
    NJB_Songid_Addframe(song, frame);
    check(NJB_Songid_Findframe(song, "Artist") == frame,
          "a second labelled frame can be found");

    NJB_Songid_Destroy(song);
    check(1, "NJB_Songid_Destroy releases the songid");

    printf("checks: %d, failures: %d\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
