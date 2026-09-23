#include <stdio.h>
#include <string.h>

#include <VtObject.h>
#include <VtApiPage.h>

/* Consumer smoke test: exercise the real library API (R34) without
 * touching the network.  VtApiPage_new/VtApiPage_setApiKey/VtApiPage_get
 * operate purely in memory; VtApiPage_put frees the object. */
int main(void) {
    struct VtApiPage *page = VtApiPage_new();
    if (!page) {
        fprintf(stderr, "FAIL: VtApiPage_new returned NULL\n");
        return 1;
    }
    VtApiPage_setApiKey(page, "test-key");
    VtApiPage_get(page);          /* bump refcount (real API call) */
    VtApiPage_put(&page);         /* drop our ref */
    if (page != NULL) {
        fprintf(stderr, "FAIL: VtApiPage_put did not NULL the pointer\n");
        return 1;
    }
    printf("PASS: c-vtapi consumer smoke test OK\n");
    return 0;
}
