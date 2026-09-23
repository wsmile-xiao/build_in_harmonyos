/*
 * Consumer test for the libcdaudio package — real API calls against the
 * installed library, headless (no CD device is opened).
 *
 * Upstream ships no test suite, so this covers the parts of the library that
 * have genuine logic independent of hardware: version reporting, the
 * LBA/MSF/frame conversion helpers (the arithmetic every playback call
 * depends on), and the documented graceful failure of cd_init_device() when
 * the device node does not exist.
 *
 * Exits non-zero as soon as any check fails.
 */

#include <stdio.h>
#include <string.h>

#include <cdaudio.h>

static int checks = 0;
static int failures = 0;

static void check(int condition, const char *what)
{
    checks++;
    if (condition)
        printf("ok %d - %s\n", checks, what);
    else {
        failures++;
        printf("not ok %d - %s\n", checks, what);
    }
}

int main(void)
{
    /* ── version reporting ─────────────────────────────────────────── */
    long version = cdaudio_getversion();
    check(version == LIBCDAUDIO_VERSION,
          "cdaudio_getversion() equals the header's LIBCDAUDIO_VERSION");
    /* (0 << 16) | (99 << 8) | 12 */
    check(version == ((0L << 16) | (99L << 8) | 12L),
          "version encodes major 0, minor 99, micro 12");

    char buffer[256];
    memset(buffer, 0, sizeof(buffer));
    cd_version(buffer, sizeof(buffer));
    check(strstr(buffer, "libcdaudio") == buffer,
          "cd_version() writes the package name at the start of the buffer");

    /* A short buffer must not overflow: cd_version() uses snprintf. */
    char tiny[8];
    memset(tiny, 0x7f, sizeof(tiny));
    cd_version(tiny, (int)sizeof(tiny));
    check(tiny[sizeof(tiny) - 1] == '\0',
          "cd_version() NUL-terminates a short buffer (no overflow)");

    /* ── LBA <-> frame conversion (150-frame / 2 s lead-in) ────────── */
    check(cd_lba_to_frames(0) == 150, "cd_lba_to_frames(0) == 150");
    check(cd_lba_to_frames(1000) == 1150, "cd_lba_to_frames(1000) == 1150");
    check(cd_frames_to_lba(150) == 0, "cd_frames_to_lba(150) == 0");
    check(cd_frames_to_lba(1000) == 850, "cd_frames_to_lba(1000) == 850");
    check(cd_frames_to_lba(149) == 0,
          "cd_frames_to_lba() clamps frames below the lead-in to 0");

    /* ── MSF <-> frame conversion (75 frames per second) ───────────── */
    struct disc_timeval zero = {0, 0, 0};
    struct disc_timeval oneSecond = {0, 1, 0};
    struct disc_timeval oneMinute = {1, 0, 0};
    struct disc_timeval mixed = {1, 2, 3};

    check(cd_msf_to_frames(zero) == 0, "cd_msf_to_frames(00:00:00) == 0");
    check(cd_msf_to_frames(oneSecond) == 75,
          "cd_msf_to_frames(00:01:00) == 75");
    check(cd_msf_to_frames(oneMinute) == 4500,
          "cd_msf_to_frames(01:00:00) == 4500");
    check(cd_msf_to_frames(mixed) == 4653,
          "cd_msf_to_frames(01:02:03) == 4653");

    struct disc_timeval roundTrip;
    cd_frames_to_msf(&roundTrip, 4653);
    check(roundTrip.minutes == 1 && roundTrip.seconds == 2 &&
              roundTrip.frames == 3,
          "cd_frames_to_msf(4653) yields 01:02:03");

    /* LBA 0 is MSF 00:02:00 (the lead-in). */
    cd_lba_to_msf(&roundTrip, 0);
    check(roundTrip.minutes == 0 && roundTrip.seconds == 2 &&
              roundTrip.frames == 0,
          "cd_lba_to_msf(0) yields 00:02:00");

    /* cd_msf_to_lba() uses a strict `> 150` guard. */
    struct disc_timeval leadIn = {0, 2, 0};
    struct disc_timeval leadInPlusOne = {0, 2, 1};
    check(cd_msf_to_lba(leadIn) == 0,
          "cd_msf_to_lba(00:02:00) == 0 (guard boundary)");
    check(cd_msf_to_lba(leadInPlusOne) == 1,
          "cd_msf_to_lba(00:02:01) == 1");

    /* Round trips across a spread of addresses, including awkward ones. */
    static const int addresses[] = {0, 1, 74, 75, 150, 151, 4500, 12345,
                                    449999};
    int roundTrips = 1;
    for (size_t i = 0; i < sizeof(addresses) / sizeof(addresses[0]); i++) {
        struct disc_timeval value;
        cd_lba_to_msf(&value, addresses[i]);
        if (cd_msf_to_lba(value) != addresses[i]) {
            printf("# round trip failed for lba %d\n", addresses[i]);
            roundTrips = 0;
        }
    }
    check(roundTrips, "cd_lba_to_msf()/cd_msf_to_lba() round-trip exactly");

    /* ── device handling without hardware ─────────────────────────── */
    int descriptor = cd_init_device((char *)"/nonexistent/cdrom/device");
    check(descriptor < 0,
          "cd_init_device() on a missing device node fails with a negative value");

    /* /dev/null is openable but is not a CD device.  The library must never
     * report a usable CD interface for it, whichever way it gets there: on
     * this platform cd_init_device() refuses it up front (its mount-table
     * probe fails), and if it did hand out a descriptor every CD operation
     * on it would have to fail. */
    descriptor = cd_init_device((char *)"/dev/null");
    int usable = 0;
    if (descriptor >= 0) {
        struct disc_info info;
        memset(&info, 0, sizeof(info));
        usable = cd_stat(descriptor, &info) >= 0;
        cd_finish(descriptor);
    }
    check(!usable,
          "an openable non-CD node is never reported as a usable CD interface");

    printf("1..%d\n", checks);
    printf("# %d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
