/* test.c — Consumer test for caps LADSPA plugin library (R34: calls real API)
 *
 * caps exports ladspa_descriptor() with C linkage as the standard LADSPA
 * entry point. This test verifies the function is callable and returns
 * a non-NULL descriptor for the first plugin (index 0).
 */
#include <stdio.h>

/* LADSPA plugin entry point — exported by caps.so with C linkage */
extern const void *ladspa_descriptor(unsigned long index);

int main(void) {
    const void *desc = ladspa_descriptor(0);
    if (!desc) {
        fprintf(stderr, "FAIL: ladspa_descriptor(0) returned NULL\n");
        return 1;
    }
    printf("OK: caps LADSPA plugin descriptor loaded (index 0)\n");
    return 0;
}
