#include <stdio.h>
#include <string.h>

#if __has_include(<libmm-glib.h>)
#include <libmm-glib.h>
#elif __has_include(<ModemManager.h>)
#include <ModemManager.h>
#else
#error "No mm-glib umbrella header found (expected libmm-glib.h)"
#endif

/* Consumer-side smoke test for the mm-glib client library.
 * All cases call real library APIs; no D-Bus daemon is required.
 * Results use internal deterministic counters (no stdout scraping):
 * the program itself emits the HMBS_TEST_PACKAGE_RESULT marker.
 */
int main(void) {
    int passed = 0;
    const int total = 4;

    /* Case 1: error domain quark must be non-zero. */
    if (mm_core_error_quark() != 0) {
        printf("CASE 1: PASS (mm_core_error_quark non-zero)\n");
        passed++;
    } else {
        printf("CASE 1: FAIL (mm_core_error_quark is 0)\n");
    }

    /* Case 2: modem state DISABLED maps to "disabled". */
    const char *s = mm_modem_state_get_string(MM_MODEM_STATE_DISABLED);
    if (s != NULL && strcmp(s, "disabled") == 0) {
        printf("CASE 2: PASS (DISABLED -> \"%s\")\n", s);
        passed++;
    } else {
        printf("CASE 2: FAIL (DISABLED -> \"%s\")\n", s ? s : "(null)");
    }

    /* Case 3: modem state UNKNOWN maps to "unknown". */
    s = mm_modem_state_get_string(MM_MODEM_STATE_UNKNOWN);
    if (s != NULL && strcmp(s, "unknown") == 0) {
        printf("CASE 3: PASS (UNKNOWN -> \"%s\")\n", s);
        passed++;
    } else {
        printf("CASE 3: FAIL (UNKNOWN -> \"%s\")\n", s ? s : "(null)");
    }

    /* Case 4: modem state REGISTERED maps to "registered". */
    s = mm_modem_state_get_string(MM_MODEM_STATE_REGISTERED);
    if (s != NULL && strcmp(s, "registered") == 0) {
        printf("CASE 4: PASS (REGISTERED -> \"%s\")\n", s);
        passed++;
    } else {
        printf("CASE 4: FAIL (REGISTERED -> \"%s\")\n", s ? s : "(null)");
    }

    printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":%s,\"command\":\"./test_mm\",\"discovered\":%d,\"passedCount\":%d}\n",
           passed == total ? "true" : "false", total, passed);
    return passed == total ? 0 : 1;
}
