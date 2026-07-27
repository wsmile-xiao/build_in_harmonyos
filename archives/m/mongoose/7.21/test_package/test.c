#include "mongoose.h"
#include <stdio.h>
#include <string.h>

int main(void) {
    /* Check version */
    printf("MG_VERSION: %s\n", MG_VERSION);

    /* Initialize event manager */
    struct mg_mgr mgr;
    mg_mgr_init(&mgr);

    /* Test mg_str */
    struct mg_str s = mg_str("hello world");
    if (s.len != 11) {
        printf("FAIL: mg_str len expected 11, got %zu\n", s.len);
        mg_mgr_free(&mgr);
        return 1;
    }

    /* Test mg_match */
    struct mg_str pattern = mg_str("hello*");
    if (!mg_match(s, pattern, NULL)) {
        printf("FAIL: mg_match failed\n");
        mg_mgr_free(&mgr);
        return 1;
    }

    printf("All tests passed\n");
    mg_mgr_free(&mgr);
    return 0;
}
