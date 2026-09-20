/* Consumer test for the installed libahp-gt package.
 *
 * The library drives an AHP GT stepper controller over a serial port, so most
 * getters/setters are guarded by ``ahp_gt_is_detected()`` and become no-ops
 * without hardware.  The checks below therefore only use the parts of the
 * public API that are well defined while disconnected: the version constant,
 * the debug level and application name, the axes limit (unguarded), the
 * "disconnected" state and the invalid file descriptor.
 */
#include <stdio.h>
#include <string.h>

#include <ahp/ahp_gt.h>

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
    static char app_name[] = "conan-consumer-test";

    setvbuf(stdout, NULL, _IOLBF, 0);

    /* AHP_GT_VERSION is 0x${MAJOR}${MINOR}${RELEASE} => 0x173 for 1.7.3 */
    check(ahp_gt_get_version() == 0x173u,
          "ahp_gt_get_version reports 1.7.3 (0x173)");

    ahp_set_debug_level(2);
    check(ahp_get_debug_level() == 2, "debug level round trip");
    ahp_set_debug_level(0);
    check(ahp_get_debug_level() == 0, "debug level can be reset");

    ahp_set_app_name(app_name);
    check(strcmp(ahp_get_app_name(), app_name) == 0,
          "application name round trip");

    ahp_gt_set_axes_limit(3);
    check(ahp_gt_get_axes_limit() == 3,
          "axes limit round trip (unguarded setting)");

    check(ahp_gt_get_current_device() >= 0,
          "current device index is valid before any connection");

    check(ahp_gt_is_connected() == 0,
          "no controller is connected by default");
    check(ahp_gt_get_fd() == -1,
          "file descriptor is -1 while disconnected");
    check(ahp_gt_is_detected(0) == 0,
          "no controller is detected by default");

    ahp_gt_disconnect();
    check(ahp_gt_is_connected() == 0,
          "disconnect is safe while already disconnected");

    printf("checks: %d, failures: %d\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
