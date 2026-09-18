#include <stdio.h>
#include <stdlib.h>

#include <libdatovka/isds.h>

int main(void) {
    int passed = 0;
    const int discovered = 5;

    /* 1: library init must succeed (IE_SUCCESS == 0). */
    isds_error err = isds_init();
    if (err != 0) {
        fprintf(stderr, "isds_init failed: %d (%s)\n", (int)err, isds_strerror(err));
        printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"./test_libdatovka\",\"discovered\":%d,\"passedCount\":%d}\n",
               discovered, passed);
        return 1;
    }
    passed++;
    printf("CHECK-OK: isds_init\n");

    /* 2: context create must return non-NULL. */
    struct isds_ctx *ctx = isds_ctx_create();
    if (ctx == NULL) {
        fprintf(stderr, "isds_ctx_create returned NULL\n");
        printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"./test_libdatovka\",\"discovered\":%d,\"passedCount\":%d}\n",
               discovered, passed);
        isds_cleanup();
        return 2;
    }
    passed++;
    printf("CHECK-OK: isds_ctx_create\n");

    /* 3: strerror must return a message for the success code. */
    const char *msg = isds_strerror(0);
    if (msg == NULL) {
        fprintf(stderr, "isds_strerror(0) returned NULL\n");
        isds_ctx_free(&ctx);
        isds_cleanup();
        printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"./test_libdatovka\",\"discovered\":%d,\"passedCount\":%d}\n",
               discovered, passed);
        return 3;
    }
    passed++;
    printf("CHECK-OK: isds_strerror -> %s\n", msg);

    /* 4: context free must succeed and clear the pointer. */
    err = isds_ctx_free(&ctx);
    if (err != 0) {
        fprintf(stderr, "isds_ctx_free failed: %d\n", (int)err);
        isds_cleanup();
        printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"./test_libdatovka\",\"discovered\":%d,\"passedCount\":%d}\n",
               discovered, passed);
        return 4;
    }
    passed++;
    printf("CHECK-OK: isds_ctx_free\n");

    /* 5: library cleanup must succeed. */
    err = isds_cleanup();
    if (err != 0) {
        fprintf(stderr, "isds_cleanup failed: %d\n", (int)err);
        printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"./test_libdatovka\",\"discovered\":%d,\"passedCount\":%d}\n",
               discovered, passed);
        return 5;
    }
    passed++;
    printf("CHECK-OK: isds_cleanup\n");

    printf("libdatovka API assertions: %d/%d passed\n", passed, discovered);
    printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":%s,\"command\":\"./test_libdatovka\",\"discovered\":%d,\"passedCount\":%d}\n",
           passed == discovered ? "true" : "false", discovered, passed);
    return passed == discovered ? 0 : 6;
}
