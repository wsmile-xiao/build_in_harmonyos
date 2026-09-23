// pmdmini consumer smoke test — verifies the packaged static library links
// and its public C API is callable (R34: exercises the package's real API).
#include <cstdio>
#include <pmdmini.h>

int main() {
    // 1. Library must initialize without crashing.
    pmd_init();

    // 2. Sampling rate must be settable before playback.
    pmd_setrate(48000);

    // 3. pmd_is_pmd() must return 0 for a path that does not exist.
    //    (The implementation fopen()s the file and returns 0 on failure.)
    const char *fake = "/nonexistent/path/to/nothing.pmd";
    if (pmd_is_pmd(fake) != 0) {
        std::fprintf(stderr,
                     "FAIL: pmd_is_pmd() returned nonzero for a nonexistent file\n");
        pmd_stop();
        return 1;
    }

    // 4. Clean up internal state.
    pmd_stop();

    std::printf("pmdmini API smoke test: OK\n");
    return 0;
}
