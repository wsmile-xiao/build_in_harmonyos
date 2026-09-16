/* test_package for myman 0.7.1 — substantial smoke test source (R34/L0c).
 * The real assertion runs in test_package/conanfile.py::test() via self.run
 * (`myman --version` / `--help`). This C file is the L0c-required test
 * source that mirrors the same check from a C consumer's point of view.
 */
#include <stdlib.h>

int main(void) {
    /* myman --version exits 0 without a TTY; failure (missing binary,
     * broken link, missing terminfo at startup) returns non-zero. */
    if (system("myman --version > /dev/null 2>&1") != 0) {
        return 1;
    }
    return 0;
}
