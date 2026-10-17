/*
 * HarmonyOS / aarch64 specialty test for upower-glib 0.99.20
 * (task upower-glib-0.99.20-r01-pc1-53)
 *
 * Covers platform-specific behavior that the upstream self-test does not:
 *   1) Enum round-trip conversions (UpDeviceKind/State/Technology/Level)
 *      exercised on the aarch64-ohos target with the installed public headers.
 *   2) Version macros from the generated up-version.h.
 *   3) UpClient construction without a system D-Bus daemon: on HarmonyOS PC
 *      there is no org.freedesktop.UPower system bus, so up_client_new()
 *      must fail gracefully (NULL + a set error) instead of crashing — this
 *      verifies the client library's error path is sound on this platform.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libupower-glib/upower.h>

static int g_failures = 0;

static void expect_str(const char *label, const char *got,
                       const char *expected) {
    if (got == NULL || strcmp(got, expected) != 0) {
        fprintf(stderr, "FAIL %s: got '%s', expected '%s'\n",
                label, got ? got : "(null)", expected);
        g_failures++;
    }
}

static void test_enum_roundtrip(void) {
    /* Round-trip only kinds that have BOTH a to_string and a from_string
     * mapping.  Upstream quirks verified empirically:
     *   - UNKNOWN:   up_device_kind_to_string() has no explicit case and
     *                falls through to the default "unknown" branch;
     *                from_string("unknown") has no branch either and falls
     *                through to UP_DEVICE_KIND_UNKNOWN -> round-trips.
     *   - COMPUTER:  to_string returns "computer" but from_string has no
     *                "computer" branch -> not round-trippable (returns
     *                UP_DEVICE_KIND_UNKNOWN).
     * Both are asserted below as observed upstream behavior. */
    for (UpDeviceKind k = UP_DEVICE_KIND_UNKNOWN; k < UP_DEVICE_KIND_LAST; k++) {
        if (k == UP_DEVICE_KIND_COMPUTER) continue;
        const char *s = up_device_kind_to_string(k);
        if (s == NULL) {
            fprintf(stderr, "FAIL kind %d has no to_string mapping\n", (int)k);
            g_failures++;
            continue;
        }
        if (up_device_kind_from_string(s) != k) {
            fprintf(stderr, "FAIL kind round-trip for %s\n", s);
            g_failures++;
        }
    }
    /* observed upstream behavior for UNKNOWN / COMPUTER */
    expect_str("kind-unknown", up_device_kind_to_string(UP_DEVICE_KIND_UNKNOWN),
               "unknown");
    if (up_device_kind_from_string("unknown") != UP_DEVICE_KIND_UNKNOWN) {
        fprintf(stderr, "FAIL: from_string(\"unknown\") should be UNKNOWN\n");
        g_failures++;
    }
    expect_str("kind", up_device_kind_to_string(UP_DEVICE_KIND_COMPUTER),
               "computer");
    if (up_device_kind_from_string("computer") != UP_DEVICE_KIND_UNKNOWN) {
        fprintf(stderr, "FAIL: from_string(\"computer\") should be UNKNOWN "
                        "upstream (no mapping)\n");
        g_failures++;
    }
    expect_str("kind", up_device_kind_to_string(UP_DEVICE_KIND_BATTERY),
               "battery");
    expect_str("state", up_device_state_to_string(UP_DEVICE_STATE_CHARGING),
               "charging");
    expect_str("tech", up_device_technology_to_string(
                   UP_DEVICE_TECHNOLOGY_LITHIUM_ION), "lithium-ion");
    expect_str("level", up_device_level_to_string(UP_DEVICE_LEVEL_FULL),
               "full");
}

static void test_version_macros(void) {
    if (UP_MAJOR_VERSION != 0 || UP_MINOR_VERSION != 99 ||
        UP_MICRO_VERSION != 20) {
        fprintf(stderr, "FAIL version macros: %d.%d.%d\n",
                UP_MAJOR_VERSION, UP_MINOR_VERSION, UP_MICRO_VERSION);
        g_failures++;
    }
    printf("upower-glib %d.%d.%d version macros OK\n",
           UP_MAJOR_VERSION, UP_MINOR_VERSION, UP_MICRO_VERSION);
}

static void test_client_without_dbus(void) {
    /* No D-Bus daemon on HarmonyOS PC: up_client_new_full() must return NULL
     * with a set error, never crash — this verifies the client library's
     * error path is sound on this platform. */
    GError *error = NULL;
    UpClient *client = up_client_new_full(NULL, &error);
    if (client != NULL) {
        g_object_unref(client);
        fprintf(stderr, "FAIL: up_client_new_full unexpectedly succeeded\n");
        g_failures++;
        return;
    }
    if (error == NULL || error->message == NULL ||
        error->message[0] == '\0') {
        fprintf(stderr, "FAIL: up_client_new_full failed but error is empty\n");
        g_failures++;
    } else {
        printf("up_client_new_full graceful failure OK: %s\n", error->message);
    }
    if (error != NULL) {
        g_error_free(error);
    }
}

int main(void) {
    printf("upower-glib OHOS specialty test start\n");
    test_enum_roundtrip();
    test_version_macros();
    test_client_without_dbus();
    if (g_failures != 0) {
        fprintf(stderr, "upower-glib OHOS specialty test FAILED (%d)\n",
                g_failures);
        return 1;
    }
    printf("upower-glib OHOS specialty test OK\n");
    return 0;
}
