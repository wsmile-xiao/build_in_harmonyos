/* Consumer test for the openmama package (C API).
 *
 * Covers what is verifiable with the AMQP middleware bridge the package ships:
 *   - the version the package was configured with
 *   - loading the in-tree stub middleware bridge, which also pulls in the base
 *     bridge implementation shipped in the same package
 *   - loading the qpid (AMQP) middleware bridge, the component that links the
 *     qpid-proton package
 *   - the open/close lifecycle with the qpidmsg payload bridge, which the
 *     library resolves while opening
 *   - the library open/close counting API
 * Every check increments the failure counter, main() returns it, and the
 * test_package conanfile relies on the exit status.
 */
#include <stdio.h>
#include <string.h>

#include <mama/mama.h>
#include <mama/version.h>

static int failures = 0;

static void
check (int condition, const char* what)
{
    printf ("  [%s] %s\n", condition ? "ok" : "FAIL", what);
    if (!condition)
    {
        failures++;
    }
}

static void
check_status (mama_status status, mama_status expected, const char* what)
{
    if (status != expected)
    {
        printf ("  [FAIL] %s (expected %s, got %s)\n",
                what,
                mamaStatus_stringForStatus (expected),
                mamaStatus_stringForStatus (status));
        failures++;
    }
    else
    {
        printf ("  [ok] %s\n", what);
    }
}

int
main (void)
{
    mamaBridge bridge = NULL;
    mamaBridge qpidBridge = NULL;
    const char* version = NULL;
    unsigned int openCount = 0;
    mama_status status = MAMA_STATUS_OK;

    printf ("openmama consumer test (C API)\n");

    /* ---- version: proves OPENMAMA_VERSION was wired through the build ---- */
    printf ("MAMA_VERSION = %s\n", MAMA_VERSION);
    check (MAMA_VERSION_MAJOR == 6 && MAMA_VERSION_MINOR == 3,
           "compile time version macros report 6.3");
    check (NULL != strstr (MAMA_VERSION, "6.3.2"),
           "compile time version string carries the 6.3.2 release");
    check (NULL != mama_version && NULL != strstr (mama_version, "6.3.2"),
           "runtime version symbol reports 6.3.2");

    /* ---- the stub middleware bridge that ships in this package ---- */
    check_status (mama_loadBridge (&bridge, "noop"), MAMA_STATUS_OK,
                  "mama_loadBridge(\"noop\") loads the packaged stub bridge");
    check (NULL != bridge, "mama_loadBridge() returned a bridge handle");
    version = mama_getVersion (bridge);
    check (NULL != version && 0 != strlen (version),
           "mama_getVersion() reports the bridge version");

    /* ---- the AMQP middleware bridge and the open/close lifecycle ---- */
    /* qpid-proton is published for this platform, so bridge/qpid and the
     * qpidmsg payload are part of the package: loading the bridge and opening
     * the library both have to succeed, which also proves the two components
     * and their qpid-proton dependency actually work at run time. */
    check_status (mama_loadBridge (&qpidBridge, "qpid"), MAMA_STATUS_OK,
                  "mama_loadBridge(\"qpid\") loads the AMQP bridge");
    check (NULL != qpidBridge, "mama_loadBridge(\"qpid\") returned a bridge handle");

    status = mama_open ();
    check_status (status, MAMA_STATUS_OK,
                  "mama_open() completes with the qpid bridge and qpidmsg payload");
    check_status (mama_openCount (&openCount), MAMA_STATUS_OK, "mama_openCount()");
    check (2 == openCount, "both open calls are counted");

    check (NULL != mamaStatus_stringForStatus (MAMA_STATUS_OK),
           "mamaStatus_stringForStatus() is callable");

    check_status (mama_close (), MAMA_STATUS_OK, "mama_close()");
    check_status (mama_close (), MAMA_STATUS_OK, "mama_close() releases the second reference");

    printf ("%s: %d check(s) failed\n", failures ? "FAILURE" : "SUCCESS", failures);
    return failures;
}
