/* Consumer-side smoke test for libiio 0.25 (R34).
 *
 * Real API calls against the packaged library:
 *   1. iio_library_get_version()      — library identity
 *   2. iio_get_backends_count()       — backend table sanity (xml must be in)
 *   3. iio_create_xml_context_mem()   — create a context from an in-memory
 *                                       XML description (works without any
 *                                       kernel IIO hardware — the ad5541a
 *                                       demo description shipped upstream)
 *   4. Device/channel enumeration on that context:
 *      iio_context_get_devices_count / iio_context_get_device /
 *      iio_device_get_id / iio_device_get_name / iio_device_get_channels /
 *      iio_channel_get_id / iio_channel_get_attr / iio_context_get_name
 *
 * On failure the binary exits non-zero so `conan create` fails loudly.
 */
#include <stdio.h>
#include <string.h>

#include <iio.h>

/* Minimal AD5541A-style context description (same shape as upstream
 * xml/ad5541a.xml) — exercises the XML backend without hardware. */
static const char demo_xml[] =
    "<?xml version=\"1.0\" encoding=\"utf-8\"?>"
    "<!DOCTYPE context ["
    "<!ELEMENT context (device)*>"
    "<!ELEMENT device (channel | attribute)*>"
    "<!ELEMENT channel (attribute)*>"
    "<!ELEMENT attribute EMPTY>"
    "<!ATTLIST context name CDATA #REQUIRED>"
    "<!ATTLIST device id CDATA #REQUIRED name CDATA #IMPLIED>"
    "<!ATTLIST channel id CDATA #REQUIRED type CDATA #REQUIRED name CDATA #IMPLIED>"
    "<!ATTLIST attribute name CDATA #REQUIRED>"
    "]>"
    "<context name=\"local\">"
    "<device id=\"iio:device0\" name=\"ad5541a\">"
    "<channel id=\"voltage0\" type=\"output\">"
    "<attribute name=\"raw\" />"
    "<attribute name=\"scale\" />"
    "</channel>"
    "</device>"
    "</context>";

static int failures = 0;

#define CHECK(cond, msg) do { \
    if (cond) { printf("PASS: %s\n", msg); } \
    else { printf("FAIL: %s\n", msg); failures++; } \
} while (0)

int main(void)
{
    unsigned int major, minor, be_count, dev_count, chan_count;
    char git[16];
    const char *str;
    struct iio_context *ctx;
    const struct iio_device *dev;
    const struct iio_channel *chan;
    int i, xml_seen = 0;

    /* 1. Library version — must be 0.25 */
    iio_library_get_version(&major, &minor, git);
    printf("libiio version: %u.%u (git %s)\n", major, minor, git);
    CHECK(major == 0 && minor == 25, "iio_library_get_version == 0.25");

    /* 2. Backend table: with network/usb/iiod/local off, exactly the XML
     *    backend (plus local if enabled) must be present. */
    be_count = iio_get_backends_count();
    printf("backends_count: %u\n", be_count);
    CHECK(be_count >= 1, "iio_get_backends_count() >= 1");
    for (i = 0; (unsigned int)i < be_count; i++) {
        str = iio_get_backend(i);
        printf("  backend[%d]: %s\n", i, str ? str : "()");
        if (str && strcmp(str, "xml") == 0)
            xml_seen = 1;
    }
    CHECK(xml_seen == 1, "xml backend registered");

    /* 3. Create an XML context in memory — the only backend that needs
     *    no kernel IIO support. */
    ctx = iio_create_xml_context_mem(demo_xml, strlen(demo_xml));
    CHECK(ctx != NULL, "iio_create_xml_context_mem() != NULL");
    if (!ctx) {
        printf("cannot continue without a context\n");
        return 1;
    }

    /* 4. Enumerate the context: name, devices, channels, attributes. */
    str = iio_context_get_name(ctx);
    printf("context name: %s\n", str ? str : "()");
    CHECK(str != NULL, "iio_context_get_name() != NULL");

    dev_count = iio_context_get_devices_count(ctx);
    printf("devices_count: %u\n", dev_count);
    CHECK(dev_count == 1, "iio_context_get_devices_count() == 1");

    dev = iio_context_get_device(ctx, 0);
    CHECK(dev != NULL, "iio_context_get_device(0) != NULL");
    if (dev) {
        str = iio_device_get_id(dev);
        printf("device[0] id: %s\n", str ? str : "()");
        CHECK(str && strcmp(str, "iio:device0") == 0,
              "iio_device_get_id() == iio:device0");

        str = iio_device_get_name(dev);
        printf("device[0] name: %s\n", str ? str : "()");
        CHECK(str && strcmp(str, "ad5541a") == 0,
              "iio_device_get_name() == ad5541a");

        chan_count = iio_device_get_channels_count(dev);
        printf("channels_count: %u\n", chan_count);
        CHECK(chan_count == 1, "iio_device_get_channels_count() == 1");

        chan = iio_device_get_channel(dev, 0);
        CHECK(chan != NULL, "iio_device_get_channel(0) != NULL");
        if (chan) {
            str = iio_channel_get_id(chan);
            printf("channel[0] id: %s\n", str ? str : "()");
            CHECK(str && strcmp(str, "voltage0") == 0,
                  "iio_channel_get_id() == voltage0");
            CHECK(iio_channel_get_attrs_count(chan) == 2,
                  "iio_channel_get_attrs_count() == 2");
            str = iio_channel_get_attr(chan, 0);
            CHECK(str != NULL, "iio_channel_get_attr(0) != NULL");
        }
    }

    iio_context_destroy(ctx);
    printf("%s: %d failure(s)\n", failures ? "RESULT" : "RESULT", failures);
    return failures ? 1 : 0;
}
