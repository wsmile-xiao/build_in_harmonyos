/* Consumer test for the packaged smpeg library.
 *
 * It plays the role of an application that links libsmpeg and drives its
 * public C API: the version macros, object creation, the documented error
 * reporting path (SMPEG_error()/SMPEG_status()) and destruction.  A real
 * decode is not exercised because the release ships no sample stream and the
 * decoder needs a valid MPEG-1 payload; the CLI side is covered by the
 * packaged plaympeg binary.
 */
#include <stdio.h>
#include <string.h>

#include <smpeg/smpeg.h>

static int checks;
static int failures;

static void check(int condition, const char *name)
{
    checks++;
    if (condition) {
        printf("CHECK-OK: %s\n", name);
    } else {
        failures++;
        printf("CHECK-FAIL: %s\n", name);
    }
}

int main(void)
{
    SMPEG_version version;
    SMPEG_Info info;
    SMPEG *mpeg;

    memset(&version, 0, sizeof(version));
    SMPEG_VERSION(&version);
    check(version.major == SMPEG_MAJOR_VERSION && version.minor == SMPEG_MINOR_VERSION,
          "SMPEG_VERSION() fills the compile-time version macros");
    check(version.major == 0 && version.minor == 4 && version.patch == 5,
          "packaged library reports the upstream 0.4.5 version");

    memset(&info, 0, sizeof(info));
    mpeg = SMPEG_new("this-file-does-not-exist.mpg", &info, 0);
    check(mpeg != NULL, "SMPEG_new() returns an SMPEG object");
    check(SMPEG_error(mpeg) != NULL, "SMPEG_error() reports the unreadable stream");
    check(SMPEG_status(mpeg) == SMPEG_ERROR, "SMPEG_status() reports SMPEG_ERROR");

    SMPEG_getinfo(mpeg, &info);
    check(info.has_audio == 0 && info.has_video == 0,
          "SMPEG_getinfo() reports an empty stream");

    SMPEG_delete(mpeg);
    printf("SMPEG_CONSUMER_CHECKS=%d FAILURES=%d\n", checks, failures);
    if (failures == 0) {
        printf("SMPEG_CONSUMER_OK\n");
    }
    return failures == 0 ? 0 : 1;
}
