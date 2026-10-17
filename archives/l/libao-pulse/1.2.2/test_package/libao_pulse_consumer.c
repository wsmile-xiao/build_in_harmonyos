/* Consumer test for libao-pulse 1.2.2.
 *
 * The package installs two artifacts that only work together at runtime:
 *
 *   lib/libao.so.4.1.1            the core library (file/raw/wav/null
 *                                 drivers are compiled in, every other
 *                                 driver is a dlopen-ed plugin)
 *   lib/ao/plugins-4/libpulse.so  the PulseAudio output driver
 *
 * The consumer therefore drives the public <ao/ao.h> API of the installed
 * package and requires the pulse driver to register itself: that can only
 * happen if libao found, loaded and relocated the plugin module.
 */
#include <ao/ao.h>
#include <stdio.h>
#include <string.h>

static int checks = 0;
static int passed = 0;

#define CHECK(cond, msg)                                                       \
    do {                                                                       \
        checks++;                                                              \
        if (cond) {                                                            \
            passed++;                                                          \
            printf("PASS: %s\n", msg);                                         \
        } else {                                                               \
            printf("FAIL: %s\n", msg);                                         \
        }                                                                      \
    } while (0)

int main(void)
{
    int index;
    int driver_count = 0;
    int pulse;
    ao_info *info = NULL;
    ao_sample_format format;
    ao_device *device = NULL;

    ao_initialize();

    ao_info **drivers = ao_driver_info_list(&driver_count);
    CHECK(drivers != NULL && driver_count > 0,
          "ao_driver_info_list returns the loaded drivers");
    for (index = 0; index < driver_count; index++) {
        printf("INFO: driver[%d] = %s\n", index,
               drivers[index]->short_name ? drivers[index]->short_name
                                          : "(null)");
    }

    pulse = ao_driver_id("pulse");
    CHECK(pulse >= 0,
          "pulse driver registered (libao dlopen'ed lib/ao/plugins-4/libpulse.so)");

    if (pulse >= 0) {
        info = ao_driver_info(pulse);
        CHECK(info != NULL && info->short_name != NULL &&
                  strcmp(info->short_name, "pulse") == 0,
              "pulse driver info exposes short_name=pulse");
        CHECK(info != NULL && info->name != NULL && info->name[0] != '\0',
              "pulse driver info carries a display name");
        if (info != NULL) {
            printf("INFO: pulse name=%s author=%s\n",
                   info->name ? info->name : "(null)",
                   info->author ? info->author : "(null)");
        }
    }

    CHECK(ao_driver_id("oss") < 0,
          "oss driver absent (configure builds the pulse plugin only)");
    CHECK(ao_driver_id("libao-pulse-consumer-bogus") < 0,
          "unknown driver ids are rejected");

    memset(&format, 0, sizeof format);
    format.bits = 16;
    format.channels = 2;
    format.rate = 44100;
    format.byte_format = AO_FMT_NATIVE;

    /* ao_open_live must refuse a driver id that names no driver at all. */
    CHECK(ao_open_live(-1, &format, NULL) == NULL,
          "ao_open_live rejects an invalid driver id");

    if (pulse >= 0) {
        device = ao_open_live(pulse, &format, NULL);
    }
    printf("INFO: ao_open_live(pulse) -> %s\n",
           device != NULL ? "device (a PulseAudio server answered)"
                          : "NULL (no PulseAudio server on this device)");

    if (pulse < 0) {
        /* No pulse driver was registered, so nothing can have opened one. */
        CHECK(device == NULL,
              "without the pulse driver ao_open_live(pulse) yields no device");
    } else if (device == NULL) {
        /* The plugin loaded and registered, so a live open can only fail
           because no server answered: a live-output driver must report that
           rather than hand back a bogus handle. */
        CHECK(info != NULL && info->type == AO_TYPE_LIVE,
              "pulse driver is a live-output driver, so no server means no device");
    } else {
        unsigned char silence[4096];
        memset(silence, 0, sizeof silence);
        CHECK(ao_play(device, (char *)silence, sizeof silence) != 0,
              "ao_play accepts a buffer on the opened pulse device");
        ao_close(device);
        device = NULL;
    }

    ao_shutdown();
    printf("libao-pulse consumer checks: %d/%d passed\n", passed, checks);
    return (passed == checks) ? 0 : 1;
}