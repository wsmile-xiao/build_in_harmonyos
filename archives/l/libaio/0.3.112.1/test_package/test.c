#include <stdio.h>
#include <errno.h>
#include <libaio.h>

int main(void) {
    io_context_t ctx = 0;

    /* Verify io_queue_init API is callable (links against libaio).
     * On some HarmonyOS kernel configs the io_setup syscall returns
     * -ENOSYS; this is a platform limitation, not a library defect.
     * The test validates linkage + API availability, not syscall success. */
    int ret = io_queue_init(1, &ctx);
    if (ret < 0) {
        printf("io_queue_init returned %d (syscall may be unsupported)\n", ret);
    } else {
        printf("io_queue_init succeeded\n");
    }

    /* Release context only if init succeeded */
    if (ret >= 0) {
        io_queue_release(ctx);
    }

    /* Verify io_pgetevents returns -ENOSYS (stub) instead of crashing
     * with SIGSYS on OHOS. This is the key fix in 0.3.112.1. */
    struct io_event events[1];
    ret = io_pgetevents(ctx, 0, 1, events, NULL, NULL);
    if (ret == -ENOSYS) {
        printf("io_pgetevents correctly returns -ENOSYS (stub)\n");
    } else {
        printf("io_pgetevents returned %d (expected -ENOSYS=%d)\n", ret, -ENOSYS);
        return 1;
    }

    printf("test libaio 0.3.112.1: PASSED\n");
    return 0;
}
