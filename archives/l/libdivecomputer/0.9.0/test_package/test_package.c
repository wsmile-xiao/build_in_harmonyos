/*
 * test_package — libdivecomputer 0.9.0 consumer verification.
 *
 * Upstream ships no automated test suite (no `check` target, no tests/
 * directory). This program exercises the complete hardware-free public
 * API surface of the library:
 *
 *   1. dc_version / dc_version_check        — version reporting
 *   2. dc_context_new / set_loglevel /
 *      get_transports / free                — context lifecycle + the
 *                                             compiled-in transport mask
 *   3. dc_descriptor_iterator               — full enumeration of the
 *                                             supported device database
 *   4. dc_parser_new2 over a synthetic
 *      Suunto Solution profile buffer       — offline dive profile
 *                                             parsing (divetime/maxdepth
 *                                             fields), no device needed
 *   5. OHOS-specific                        — the transport mask must
 *                                             contain SERIAL, and when
 *                                             built with libusb also USB
 *                                             and USBHID; this proves the
 *                                             OHOS build kept the real
 *                                             backends compiled in rather
 *                                             than disabling transports.
 *
 * Nothing here opens a serial port, USB device or Bluetooth socket: no
 * dive computer hardware is required or emulated.
 */

#include <stdio.h>
#include <string.h>

#include <libdivecomputer/version.h>
#include <libdivecomputer/common.h>
#include <libdivecomputer/context.h>
#include <libdivecomputer/iterator.h>
#include <libdivecomputer/descriptor.h>
#include <libdivecomputer/parser.h>

/* The OHOS clang driver defines __OHOS__=1 and __linux__=1. */
#ifdef __OHOS__
#define PLATFORM_NAME "OHOS"
#elif defined(__linux__)
#define PLATFORM_NAME "Linux"
#else
#define PLATFORM_NAME "unknown"
#endif

/* A synthetic Suunto Solution dive profile.
 *
 * Layout required by src/suunto_solution_parser.c:
 *   data[0..2]  : header (skipped by the parser)
 *   data[3..]   : depth samples; 0x80 terminates the sample stream
 *   data[4]     : additional surface time bytes after the marker
 * The parser needs size >= 4, an 0x80 marker at an offset < size - 1,
 * and sample bytes in [0x01..0x7c] (raw < 0x7e and != 0x80) so they are
 * counted as depth deltas.
 */
static const unsigned char suunto_solution_profile[] = {
    0x00, 0x00, 0x00,             /* header bytes                       */
    0x0A, 0x0A, 0x0A, 0x0A,       /* four depth samples: 10 ft each     */
    0x80,                         /* end-of-samples marker              */
    0x05,                         /* surface interval byte              */
};

static int g_failures = 0;

#define CHECK(cond, msg)                                        \
    do {                                                        \
        if (cond) {                                             \
            printf("PASS: %s\n", msg);                          \
        } else {                                                \
            printf("FAIL: %s (at %s:%d)\n", msg, __FILE__, __LINE__); \
            g_failures++;                                       \
        }                                                       \
    } while (0)

static void sample_cb(dc_sample_type_t type, const dc_sample_value_t *value, void *userdata)
{
    unsigned int *count = (unsigned int *) userdata;
    (void) value;
    if (type == DC_SAMPLE_TIME || type == DC_SAMPLE_DEPTH) {
        (*count)++;
    }
}

int main(void)
{
    printf("platform: %s\n", PLATFORM_NAME);

    /* --- 1. version ---------------------------------------------------- */
    dc_version_t ver = {0, 0, 0};
    const char *version_str = dc_version(&ver);
    printf("libdivecomputer version: %s (%u.%u.%u)\n",
           version_str ? version_str : "(null)", ver.major, ver.minor, ver.micro);
    CHECK(version_str != NULL, "dc_version returns a non-NULL string");
    CHECK(ver.major == DC_VERSION_MAJOR &&
          ver.minor == DC_VERSION_MINOR &&
          ver.micro == DC_VERSION_MICRO,
          "dc_version struct matches DC_VERSION_* macros");
    CHECK(DC_VERSION_CHECK(0, 0, 1) && !DC_VERSION_CHECK(0xFF, 0, 0),
          "DC_VERSION_CHECK macro logic");
    CHECK(dc_version_check(0, 9, 0) == 1,
          "dc_version_check(0.9.0) accepts 0.9.0 (link-time C function)");
    CHECK(dc_version_check(99, 0, 0) == 0,
          "dc_version_check rejects 99.0.0");

    /* --- 2. context ---------------------------------------------------- */
    dc_context_t *context = NULL;
    dc_status_t rc = dc_context_new(&context);
    CHECK(rc == DC_STATUS_SUCCESS && context != NULL, "dc_context_new");
    if (rc != DC_STATUS_SUCCESS) {
        return 1;
    }

    rc = dc_context_set_loglevel(context, DC_LOGLEVEL_WARNING);
    CHECK(rc == DC_STATUS_SUCCESS, "dc_context_set_loglevel");

    unsigned int transports = dc_context_get_transports(context);
    printf("compiled-in transports mask: 0x%08x\n", transports);
    CHECK(transports & DC_TRANSPORT_SERIAL,
          "SERIAL transport is compiled in (POSIX termios, always on)");
    CHECK((transports & DC_TRANSPORT_BLE) == 0,
          "BLE transport is absent as upstream hard-codes transport_ble=no in 0.9.0");

#ifdef HAVE_LIBUSB_IN_BUILD
    /* Injected by test_package/conanfile.py from the recipe option. */
    CHECK(transports & DC_TRANSPORT_USB, "USB transport compiled in (libusb)");
    CHECK(transports & DC_TRANSPORT_USBHID, "USBHID transport compiled in (libusb fallback)");
#else
    printf("note: built without libusb; USB/USBHID not expected in mask\n");
#endif

    /* --- 3. descriptor database ---------------------------------------- */
    dc_iterator_t *iterator = NULL;
    rc = dc_descriptor_iterator_new(&iterator, context);
    CHECK(rc == DC_STATUS_SUCCESS && iterator != NULL,
          "dc_descriptor_iterator_new");

    unsigned int n_devices = 0;
    int seen_suunto_solution = 0;
    dc_descriptor_t *descriptor = NULL;
    if (rc == DC_STATUS_SUCCESS) {
        while ((rc = dc_iterator_next(iterator, &descriptor)) == DC_STATUS_SUCCESS) {
            const char *vendor = dc_descriptor_get_vendor(descriptor);
            const char *product = dc_descriptor_get_product(descriptor);
            dc_family_t family = dc_descriptor_get_type(descriptor);
            if (vendor && product && family != DC_FAMILY_NULL) {
                n_devices++;
                if (strcmp(vendor, "Suunto") == 0 &&
                    strcmp(product, "Solution") == 0 &&
                    family == DC_FAMILY_SUUNTO_SOLUTION) {
                    seen_suunto_solution = 1;
                }
            }
            dc_descriptor_free(descriptor);
            descriptor = NULL;
        }
        CHECK(rc == DC_STATUS_DONE, "descriptor iterator ends with DC_STATUS_DONE");
        rc = dc_iterator_free(iterator);
        CHECK(rc == DC_STATUS_SUCCESS, "dc_iterator_free");
    }
    printf("supported devices enumerated: %u\n", n_devices);
    CHECK(n_devices > 100,
          "descriptor database is populated (more than 100 devices)");
    CHECK(seen_suunto_solution, "Suunto Solution (serial, family parser) present");

    /* --- 4. offline parser --------------------------------------------- */
    /* Look up the Suunto Solution descriptor for the parser. */
    descriptor = NULL;
    iterator = NULL;
    rc = dc_descriptor_iterator_new(&iterator, NULL);
    CHECK(rc == DC_STATUS_SUCCESS, "second dc_descriptor_iterator_new (NULL context)");
    if (rc == DC_STATUS_SUCCESS) {
        while ((rc = dc_iterator_next(iterator, &descriptor)) == DC_STATUS_SUCCESS) {
            const char *vendor = dc_descriptor_get_vendor(descriptor);
            const char *product = dc_descriptor_get_product(descriptor);
            if (vendor && product &&
                strcmp(vendor, "Suunto") == 0 &&
                strcmp(product, "Solution") == 0) {
                break;
            }
            dc_descriptor_free(descriptor);
            descriptor = NULL;
        }
        dc_iterator_free(iterator);
    }
    CHECK(descriptor != NULL, "found Suunto Solution descriptor for parser test");

    if (descriptor != NULL) {
        dc_parser_t *parser = NULL;
        rc = dc_parser_new2(&parser, context, descriptor,
                            suunto_solution_profile,
                            sizeof(suunto_solution_profile));
        CHECK(rc == DC_STATUS_SUCCESS && parser != NULL,
              "dc_parser_new2 on synthetic Suunto Solution buffer");
        if (rc == DC_STATUS_SUCCESS && parser != NULL) {
            CHECK(dc_parser_get_type(parser) == DC_FAMILY_SUUNTO_SOLUTION,
                  "dc_parser_get_type returns SUUNTO_SOLUTION");

            unsigned int divetime = 0;
            rc = dc_parser_get_field(parser, DC_FIELD_DIVETIME, 0, &divetime);
            printf("parsed divetime: %u s\n", divetime);
            CHECK(rc == DC_STATUS_SUCCESS && divetime == (4 * 3 + 5) * 60,
                  "divetime field parsed from synthetic profile ((4 samples * 3 + 5) * 60)");

            /* MAXDEPTH is a double in meters (raw * 0.3048). */
            double maxdepth = 0.0;
            rc = dc_parser_get_field(parser, DC_FIELD_MAXDEPTH, 0, &maxdepth);
            printf("parsed maxdepth: %.4f m (expect 40 * 0.3048)\n", maxdepth);
            CHECK(rc == DC_STATUS_SUCCESS && maxdepth > 40 * 0.3048 - 1e-9 &&
                  maxdepth < 40 * 0.3048 + 1e-9,
                  "maxdepth field parsed from synthetic profile (4 * 10 ft)");

            unsigned int nsamples = 0;
            rc = dc_parser_samples_foreach(parser, sample_cb, &nsamples);
            CHECK(rc == DC_STATUS_SUCCESS && nsamples > 0,
                  "samples_foreach enumerates sample events offline");

            dc_parser_destroy(parser);
        }
        dc_descriptor_free(descriptor);
    }

    /* --- 5. cleanup ----------------------------------------------------- */
    rc = dc_context_free(context);
    CHECK(rc == DC_STATUS_SUCCESS, "dc_context_free");

    printf("%s: %d failure(s)\n", PLATFORM_NAME, g_failures);
    return g_failures == 0 ? 0 : 1;
}
