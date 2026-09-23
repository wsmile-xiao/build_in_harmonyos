/* test_package for libaccounts 1.17 (upstream project: libaccounts-glib).
 * Verifies the package can be linked and that the core GObject types
 * (AgManager, AgAccountService) are registered when the library loads.
 * Uses flat includes (ag-manager.h / ag-account-service.h) that only
 * pull in core glib headers, mirroring the 1.27 test_package approach. */
#include <ag-manager.h>
#include <ag-account-service.h>
#include <stdio.h>

int main(void) {
    /* Test 1: AgManager GType must be registered after library init */
    GType ag_type = ag_manager_get_type();
    if (ag_type == 0) {
        fprintf(stderr, "FAIL: AgManager GType not registered\n");
        return 1;
    }
    printf("OK: AgManager GType registered: %lu\n", (unsigned long)ag_type);

    /* Test 2: AgAccountService GType must be registered */
    GType ag_as_type = ag_account_service_get_type();
    if (ag_as_type == 0) {
        fprintf(stderr, "FAIL: AgAccountService GType not registered\n");
        return 1;
    }
    printf("OK: AgAccountService GType registered: %lu\n", (unsigned long)ag_as_type);

    /* Test 3: platform identification */
#ifdef __OHOS__
    printf("OK: running on HarmonyOS\n");
#else
    printf("INFO: host build (not HarmonyOS)\n");
#endif

    printf("libaccounts test: version 1.17 PASSED\n");
    return 0;
}
