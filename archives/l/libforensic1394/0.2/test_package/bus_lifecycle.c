/*
 * Behavioural consumer test for the installed libforensic1394 package.
 *
 * Exercises the documented bus lifecycle on the machine that runs the test:
 * allocate a bus, attach user data, request the SBP-2 unit directory,
 * enumerate devices, and destroy the bus.  The expected results depend on
 * whether a local FireWire controller is present, so the test probes
 * /dev/fw* (the same source the library globs) and asserts the documented
 * outcome for that case instead of accepting any value.
 *
 * A host without FireWire must still be safe: the device list comes back
 * non-NULL and empty, enable_sbp2 reports a general I/O error, and destroy
 * releases everything without crashing.
 *
 * Note: upstream forensic1394_alloc() uses malloc() and never initialises the
 * bus user-data slot, so the value returned before the first
 * forensic1394_set_bus_user_data() call is indeterminate; the test asserts the
 * documented set/get round trip instead of relying on that slot being NULL.
 */

#include <forensic1394.h>

#include <glob.h>
#include <stdio.h>
#include <string.h>

static int checks;

#define CHECK(cond)                                                          \
    do {                                                                     \
        ++checks;                                                            \
        if (!(cond)) {                                                       \
            fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);  \
            return 1;                                                        \
        }                                                                    \
    } while (0)

/* Report whether the machine exposes a Juju FireWire node (/dev/fw*). */
static int local_firewire_node(void)
{
    glob_t matches;
    int present = 0;

    if (glob("/dev/fw*", 0, NULL, &matches) == 0)
    {
        present = matches.gl_pathc > 0;
        globfree(&matches);
    }

    return present;
}

int main(void)
{
    int has_fw = local_firewire_node();
    forensic1394_bus *bus;
    forensic1394_dev **devices;
    forensic1394_result result;
    int marker = 0;
    int ndev = -1;
    int i;
    int counted;

    printf("forensic1394_bus_lifecycle: local /dev/fw* present = %s\n",
           has_fw ? "yes" : "no");

    bus = forensic1394_alloc();
    CHECK(bus != NULL);

    /* User data round-trips through the accessors. */
    forensic1394_set_bus_user_data(bus, &marker);
    CHECK(forensic1394_get_bus_user_data(bus) == (void *) &marker);

    /* SBP-2 activation needs a local Juju node; without one the library
       reports a general I/O error instead of pretending to succeed. */
    result = forensic1394_enable_sbp2(bus);
    if (has_fw)
    {
        CHECK(result <= FORENSIC1394_RESULT_SUCCESS);
    }
    else
    {
        CHECK(result == FORENSIC1394_RESULT_IO_ERROR);
    }

    /* Device enumeration always returns a NULL-terminated list. */
    devices = forensic1394_get_devices(bus, &ndev, NULL);
    CHECK(devices != NULL);

    counted = 0;
    while (devices[counted] != NULL)
    {
        ++counted;
    }

    if (has_fw)
    {
        /* With a controller present the count follows the list length; an
           empty list is still possible when no peer is attached. */
        if (counted > 0)
        {
            CHECK(ndev == counted);
        }
        else
        {
            CHECK(ndev <= 0);
        }
    }
    else
    {
        /* Without a controller the list is empty and the count is 0. */
        CHECK(counted == 0);
        CHECK(ndev == 0);
    }

    /* Devices, when present, must expose identity text and start closed. */
    for (i = 0; i < counted; ++i)
    {
        CHECK(forensic1394_get_device_product_name(devices[i]) != NULL);
        CHECK(forensic1394_get_device_vendor_name(devices[i]) != NULL);
        CHECK(forensic1394_is_device_open(devices[i]) == 0);
    }

    forensic1394_destroy(bus);

    /* Repeated alloc/destroy cycles must stay clean. */
    for (i = 0; i < 3; ++i)
    {
        bus = forensic1394_alloc();
        CHECK(bus != NULL);
        forensic1394_destroy(bus);
    }

    printf("forensic1394_bus_lifecycle: %d checks passed\n", checks);
    return 0;
}
