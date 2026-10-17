/* Consumer test for the openmama package (C++ bindings).
 *
 * Mirrors the C test through Wombat::Mama, which is what makes this a real
 * check that libmamacpp is usable and not just installed: a bridge is loaded,
 * the property subsystem is exercised, and the open/close lifecycle is driven
 * through the wrappers.
 */
#include <cstdio>
#include <cstring>
#include <string>

#include <mama/mamacpp.h>

using namespace Wombat;

static int failures = 0;

static void
check (bool condition, const char* what)
{
    std::printf ("  [%s] %s\n", condition ? "ok" : "FAIL", what);
    if (!condition)
    {
        failures++;
    }
}

int
main ()
{
    mamaBridge bridge = NULL;
    const char* version = NULL;

    std::printf ("openmama consumer test (C++ bindings)\n");

    try
    {
        bridge = Mama::loadBridge ("noop");
        check (NULL != bridge, "Mama::loadBridge(\"noop\")");

        version = Mama::getVersion (bridge);
        check (NULL != version && 0 != std::strlen (version),
               "Mama::getVersion() reports the bridge version");

        /* property subsystem round trip (used by the whole library) */
        Mama::setProperty ("openmama.test.property", "openmama.test.value");
        check (std::string ("openmama.test.value") ==
                   std::string (Mama::getProperty ("openmama.test.property")),
               "Mama::setProperty() / Mama::getProperty() round trip");

        /* the AMQP bridge the package ships, and the qpidmsg payload the
         * library resolves while opening: both are built on the published
         * qpid-proton package, so the lifecycle completes instead of
         * reporting a crop. */
        bridge = Mama::loadBridge ("qpid");
        check (NULL != bridge, "Mama::loadBridge(\"qpid\") loads the AMQP bridge");

        bool opened = false;
        try
        {
            Mama::open ();
            opened = true;
        }
        catch (const MamaStatus& status)
        {
            check (false, ("Mama::open() threw " +
                           std::string (status.toString ())).c_str ());
        }
        catch (...)
        {
            check (false, "Mama::open() threw an unexpected exception");
        }
        check (opened, "Mama::open() completes with the qpid bridge and qpidmsg payload");

        /* openCount and close drive the same library entry points, so they
         * have to succeed as well */
        if (opened)
        {
            check (2 == Mama::openCount (), "both open calls are counted");
            Mama::close ();
        }
    }
    catch (const MamaStatus& status)
    {
        std::printf ("  [FAIL] unexpected MamaStatus exception: %s\n",
                     status.toString ());
        failures++;
    }
    catch (...)
    {
        std::printf ("  [FAIL] unexpected exception from the C++ bindings\n");
        failures++;
    }

    std::printf ("%s: %d check(s) failed\n", failures ? "FAILURE" : "SUCCESS", failures);
    return failures;
}
