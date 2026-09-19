/*
 * consumer test for upower-glib 0.99.20 (HarmonyOS PC)
 *
 * Uses only installed public headers and public API:
 *   - <libupower-glib/upower.h> umbrella header (up-version.h/up-types.h
 *     reject direct inclusion) and its enum conversion helpers — callable
 *     without a D-Bus daemon.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libupower-glib/upower.h>

int main(void) {
    int failures = 0;

    /* version macros from up-version.h.in */
    if (UP_MAJOR_VERSION != 0 || UP_MINOR_VERSION != 99 || UP_MICRO_VERSION != 20) {
        fprintf(stderr, "unexpected version: %d.%d.%d\n",
                UP_MAJOR_VERSION, UP_MINOR_VERSION, UP_MICRO_VERSION);
        failures++;
    }

    /* public enum -> string conversions (up_types.c) */
    const char *kind = up_device_kind_to_string(UP_DEVICE_KIND_BATTERY);
    if (kind == NULL || strcmp(kind, "battery") != 0) {
        fprintf(stderr, "up_device_kind_to_string(BATTERY) -> %s\n",
                kind ? kind : "(null)");
        failures++;
    }

    const char *state = up_device_state_to_string(UP_DEVICE_STATE_CHARGING);
    if (state == NULL || strcmp(state, "charging") != 0) {
        fprintf(stderr, "up_device_state_to_string(CHARGING) -> %s\n",
                state ? state : "(null)");
        failures++;
    }

    const char *tech = up_device_technology_to_string(UP_DEVICE_TECHNOLOGY_LITHIUM_ION);
    if (tech == NULL || strcmp(tech, "lithium-ion") != 0) {
        fprintf(stderr, "up_device_technology_to_string(LITHIUM_ION) -> %s\n",
                tech ? tech : "(null)");
        failures++;
    }

    const char *level = up_device_level_to_string(UP_DEVICE_LEVEL_FULL);
    if (level == NULL || strcmp(level, "full") != 0) {
        fprintf(stderr, "up_device_level_to_string(FULL) -> %s\n",
                level ? level : "(null)");
        failures++;
    }

    /* round-trip: from-string parsing */
    if (up_device_kind_from_string("battery") != UP_DEVICE_KIND_BATTERY) {
        fprintf(stderr, "up_device_kind_from_string(\"battery\") mismatch\n");
        failures++;
    }

    if (failures != 0) {
        fprintf(stderr, "upower-glib consumer test FAILED (%d)\n", failures);
        return 1;
    }
    printf("upower-glib consumer test OK: version=%d.%d.%d kind=%s state=%s tech=%s level=%s\n",
           UP_MAJOR_VERSION, UP_MINOR_VERSION, UP_MICRO_VERSION,
           kind, state, tech, level);
    return 0;
}