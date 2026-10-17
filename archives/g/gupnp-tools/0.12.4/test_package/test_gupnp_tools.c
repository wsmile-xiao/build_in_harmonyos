/* test_gupnp_tools.c — structural companion for the gupnp-tools L1 test.
 *
 * gupnp-tools is an application package: the product is the installed
 * binaries (gssdp-discover, gupnp-event-dumper). There are no public
 * headers/libraries to compile against, so the substantive verification
 * (R34) is the execution of the packaged binaries in conanfile.py test():
 *   gssdp-discover --help      -> real GSSDP CLI help, exit 0
 *   gssdp-discover -n 1        -> real SSDP discovery (1 s), exit 0
 *   gupnp-event-dumper         -> bounded run, clean SIGTERM shutdown, exit 0
 * This companion source keeps the CMake build meaningful (it verifies the
 * conan toolchain can still compile & link a trivial program in the same
 * environment that will run the tools) and prints what will be executed.
 */
#include <stdio.h>

int
main (void)
{
        printf ("gupnp-tools test_package: toolchain OK; "
                "binaries under test: gssdp-discover, gupnp-event-dumper\\n");
        return 0;
}
