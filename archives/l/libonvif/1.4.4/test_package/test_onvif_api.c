/*
 * libonvif consumer test (test_package).
 *
 * Compiles against the packaged public header onvif.h and links the
 * packaged onvif library, then exercises offline-safe exported C API
 * functions with hard assertions:
 *   - getUUID / initializeSession: UUID generation and session init
 *   - prefix2mask / mask2prefix: prefix <-> dotted-quad netmask math
 *   - clearData: observable struct reset
 *
 * Exit code 0 = every assertion passed; nonzero = at least one failure.
 * Note: onvif.h does not include its own libxml2 headers, so a consumer
 * must include libxml2 before onvif.h (upstream header quirk).
 */
#include <stdio.h>
#include <string.h>

#include <libxml/tree.h>

#include "onvif.h"

static int failures = 0;

static void check(int cond, const char *what)
{
    if (cond) {
        printf("PASS: %s\n", what);
    } else {
        printf("FAIL: %s\n", what);
        failures++;
    }
}

static int is_uuid_value(const char *s)
{
    /* canonical 8-4-4-4-12 hexadecimal layout */
    if (strlen(s) != 36) {
        return 0;
    }
    for (int i = 0; i < 36; i++) {
        char c = s[i];
        if (i == 8 || i == 13 || i == 18 || i == 23) {
            if (c != '-') {
                return 0;
            }
        } else if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') ||
                     (c >= 'A' && c <= 'F'))) {
            return 0;
        }
    }
    return 1;
}

static int is_uuid(const char *s)
{
    /* the library emits the "urn:uuid:" prefix in its generated ids */
    if (strncmp(s, "urn:uuid:", 9) == 0) {
        s += 9;
    }
    return is_uuid_value(s);
}

int main(void)
{
    char mask[128];
    char uuid[47];

    /* 1) getUUID: generates a well-formed UUID string */
    getUUID(uuid);
    printf("INFO: getUUID -> %s\n", uuid);
    check(is_uuid(uuid), "getUUID returns a well-formed UUID");

    /* 2) prefix2mask: CIDR prefix to dotted-quad netmask */
    prefix2mask(24, mask);
    printf("INFO: prefix2mask(24) -> %s\n", mask);
    check(strcmp(mask, "255.255.255.0") == 0, "prefix2mask(24) == 255.255.255.0");

    prefix2mask(16, mask);
    printf("INFO: prefix2mask(16) -> %s\n", mask);
    check(strcmp(mask, "255.255.0.0") == 0, "prefix2mask(16) == 255.255.0.0");

    /* 3) mask2prefix: dotted-quad netmask back to CIDR prefix */
    int prefix = mask2prefix((char *)"255.255.255.0");
    check(prefix == 24, "mask2prefix(255.255.255.0) == 24");

    prefix = mask2prefix((char *)"255.255.0.0");
    check(prefix == 16, "mask2prefix(255.255.0.0) == 16");

    /* 4) initializeSession: fills the UUID and the discovery message id */
    struct OnvifSession session;
    memset(&session, 0, sizeof(session));
    initializeSession(&session);
    check(session.discovery_msg_id == 1, "initializeSession sets discovery_msg_id = 1");
    check(is_uuid(session.uuid), "initializeSession fills the session UUID");
    closeSession(&session);

    /* 5) clearData: caller-filled fields are reset by the library */
    struct OnvifData data;
    memset(&data, 0, sizeof(data));
    strcpy(data.videoEncoderConfigurationToken, "marker-token");
    strcpy(data.camera_name, "marker-camera");
    data.width = 1920;
    data.frame_rate = 30;
    clearData(&data);
    check(data.videoEncoderConfigurationToken[0] == '\0', "clearData clears the encoder token");
    check(data.camera_name[0] == '\0', "clearData clears the camera name");
    check(data.width == 0, "clearData resets width");
    check(data.frame_rate == 0, "clearData resets frame_rate");

    if (failures == 0) {
        printf("ALL TESTS PASSED\n");
        return 0;
    }
    printf("%d TEST(S) FAILED\n", failures);
    return 1;
}
