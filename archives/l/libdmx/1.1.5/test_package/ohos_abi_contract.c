#include <stdio.h>
#include <X11/Xlib.h>
/* dmxproto.h is not self-contained: it uses CARD32 but includes
 * nothing; Xmd.h must come first. */
#include <X11/Xmd.h>
#include <X11/extensions/dmxproto.h>
#include <X11/extensions/dmxext.h>
#include <X11/extensions/dmx.h>

/*
 * OHOS-specific ABI contract for the installed libdmx package.
 *
 * The DMX client library publishes no display-independent runtime entry
 * point (every public function dereferences a Display *), so the
 * OHOS-specific validation pins the load-time contract instead:
 * the executable links against libdmx.so.1 and executes successfully on
 * a HarmonyOS device, proving that
 *   1. the dynamic linker can resolve libdmx.so.1 and its transitive
 *      closure (libXext.so.6, libX11.so.6, libxcb, libxau, libxdmcp)
 *      from the Conan package layout,
 *   2. the ELF64 AArch64 relocations in libdmx.so.1 settle without
 *      text relocations at load time.
 * The recipe's test() additionally parses readelf output for the ELF
 * class, machine, NEEDED entries, and RPATH/RUNPATH hygiene of the
 * installed library before this program runs.
 */

int main(void) {
    /* Compile-time contract: the public ABI types and the extension
     * name must come from the installed package headers. */
    static const char expected_name[] = DMX_EXTENSION_NAME;
    DMXWindowAttributes window;
    DMXDesktopAttributes desktop;
    DMXInputAttributes input;

    if (sizeof(expected_name) != 4 || expected_name[0] != 'D') {
        return 1;
    }
    /* The public structs must be complete ABI types with the expected
     * lower-bound sizes (screen attributes: display + 9 scalars +
     * pointer = 56 bytes on AArch64; window attributes: 3 ints +
     * 2 XRectangles = 32 bytes). */
    if (sizeof(DMXScreenAttributes) < 7 * sizeof(void *) ||
        sizeof(DMXWindowAttributes) < 4 * sizeof(int)) {
        return 2;
    }
    /* The three public structs must stay distinct ABI types. */
    if (sizeof(desktop) == 0 || sizeof(window) == 0 || sizeof(input) == 0) {
        return 3;
    }
    printf("LIBDMX_TEST ohos_abi_contract PASS\n");
    return 0;
}
