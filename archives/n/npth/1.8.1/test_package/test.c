#include <stdio.h>
#include <stdlib.h>
#include <npth.h>

static int thread_ran = 0;

static void *thread_func(void *arg)
{
    (void)arg;
    thread_ran = 1;
    return NULL;
}

int main(void)
{
    int err;
    npth_t tid;
    void *retval;

    err = npth_init();
    if (err) {
        fprintf(stderr, "npth_init failed: %d\n", err);
        return 1;
    }

    err = npth_create(&tid, NULL, thread_func, NULL);
    if (err) {
        fprintf(stderr, "npth_create failed: %d\n", err);
        return 1;
    }

    err = npth_join(tid, &retval);
    if (err) {
        fprintf(stderr, "npth_join failed: %d\n", err);
        return 1;
    }

    if (!thread_ran) {
        fprintf(stderr, "thread did not run\n");
        return 1;
    }

    printf("npth 1.8 test: OK (thread created and joined)\n");
    return 0;
}
