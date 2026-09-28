/*
 * abi_contract.c — pinned layout, version and no-display behaviour.
 *
 * The size/offset sites below are _Static_assert, so a consumer that compiles
 * against the installed headers cannot silently get a different layout than
 * the one this package was verified with; the version macros identify the
 * 1.2.4 API/ABI line.  The two runtime sites describe the measured behaviour
 * of this platform: there is no X server, so opening the default display must
 * fail, which is exactly why no test here claims that any GUI path works.
 */

#include <stddef.h>
#include <stdio.h>

#include <X11/Xlib.h>
#include <forms.h>

#define CHECK(cond, msg)                                                     \
    do {                                                                     \
        if (!(cond)) {                                                       \
            fprintf(stderr, "FAIL: %s\n", msg);                              \
            return 1;                                                        \
        }                                                                    \
        printf("ok: %s\n", msg);                                             \
    } while (0)

_Static_assert(sizeof(FL_PUP_ENTRY) == 32, "FL_PUP_ENTRY is 32 bytes on LP64");
_Static_assert(offsetof(FL_PUP_ENTRY, text) == 0, "FL_PUP_ENTRY.text at 0");
_Static_assert(offsetof(FL_PUP_ENTRY, callback) == 8, "FL_PUP_ENTRY.callback at 8");
_Static_assert(offsetof(FL_PUP_ENTRY, shortcut) == 16, "FL_PUP_ENTRY.shortcut at 16");
_Static_assert(offsetof(FL_PUP_ENTRY, mode) == 24, "FL_PUP_ENTRY.mode at 24");
_Static_assert(sizeof(FL_COLOR) == sizeof(unsigned long), "FL_COLOR keeps its width");
_Static_assert(FL_VERSION == 1, "FL_VERSION == 1");
_Static_assert(FL_REVISION == 2, "FL_REVISION == 2 (xforms 1.2)");

int main(void)
{
    /* SUMMARY: cases=1 static=8 runtime=2 */
    CHECK(sizeof(FL_PUP_ENTRY) == 32, "runtime: sizeof(FL_PUP_ENTRY) == 32");

    /* The measured failure form on this platform: no X server is reachable,
     * so no display-dependent call can be exercised.  Asserting the failure
     * keeps the test honest — it must not be read as "GUI works". */
    Display *display = XOpenDisplay(NULL);
    if (display != NULL) {
        XCloseDisplay(display);
        CHECK(0, "XOpenDisplay(NULL) must fail: this platform has no X server");
    }
    printf("ok: XOpenDisplay(NULL) fails as measured on HarmonyOS PC\n");
    return 0;
}
