/*
 * test_package/test.c — kylin-burner consumer API reference.
 *
 * Compile-only consumer source (compiled by test_package/conanfile.py):
 * exercises the public header <burner-units.h> shipped by the
 * libburner-media3 install (installed under include/burner3, which is on
 * the compiler's -I path), which is self-contained on glib and provides
 * the speed-unit conversion macros used by the application.
 *
 * The runtime verification of the package is performed by test.sh
 * (executes the packaged `bin/burner` launcher --version, checks the real
 * ELF bin/burner-bin and the shared libraries).  The GTK3 GUI/CLI binary
 * itself needs a desktop session; on headless OHOS workers the launcher
 * answers --version/--help.
 */
#include <burner-units.h>
#include <stdio.h>

int main(void)
{
    guint rate = BURNER_SPEED_TO_RATE_CD(1);
    if (rate != CD_RATE) {
        fprintf(stderr, "BURNER_SPEED_TO_RATE_CD(1) = %u, expected %u\n",
                (unsigned) rate, (unsigned) CD_RATE);
        return 1;
    }
    printf("kylin-burner burner-units.h API OK (CD_RATE=%u)\n",
           (unsigned) CD_RATE);
    return 0;
}
