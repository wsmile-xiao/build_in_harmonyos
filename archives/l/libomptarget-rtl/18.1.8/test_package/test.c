/*
 * test_libomptarget_rtl.c — L1 smoke test for the libomptarget RTL plugin.
 *
 * Links against libomptarget.rtl.aarch64.so (the aarch64 generic-ELF64
 * offloading plugin) and calls a real plugin API:
 *   - __tgt_rtl_number_of_devices(): number of available offloading devices
 *     (host-only platform returns 0).
 *
 * Build+link verification proves the plugin library is installable and its
 * public __tgt_rtl_* interface links correctly (R34: real dependency).
 * Runtime execution is attempted; on HarmonyOS musl the loader rejects ELF
 * with .gnu.version_r (LLVM_20.1 symbol-version requirements from libLLVM)
 * returning EACCES — a documented musl compatibility limitation identical to
 * the libomptarget recipe, so the run is skipped with that reason recorded.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

/* libomptarget RTL plugin public interface (C-compatible subset). */
extern int32_t __tgt_rtl_number_of_devices(void);

int main(void) {
    int32_t n_dev;

    /* Exercise a real plugin entry point: number of offloading devices. */
    n_dev = __tgt_rtl_number_of_devices();

    /* Host-only platform: must be 0 (no offloading device). */
    if (n_dev != 0) {
        fprintf(stderr, "FAIL: __tgt_rtl_number_of_devices() = %d (expected 0)\n",
                (int)n_dev);
        return 1;
    }

    printf("PASS: libomptarget RTL plugin linked and queried, devices=%d\n",
           (int)n_dev);
    return 0;
}
