#include <pth.h>
#include <stdio.h>

static void *worker(void *arg)
{
    long value = (long)arg;
    return (void *)(value + 1);
}

int main(void)
{
    pth_t thread;
    void *result = NULL;

    if (!pth_init()) {
        fprintf(stderr, "pth_init failed\n");
        return 2;
    }

    thread = pth_spawn(PTH_ATTR_DEFAULT, worker, (void *)41);
    if (thread == NULL) {
        fprintf(stderr, "pth_spawn failed\n");
        return 3;
    }

    if (!pth_join(thread, &result)) {
        fprintf(stderr, "pth_join failed\n");
        return 4;
    }

    printf("PTH_JOIN_RESULT=%ld\n", (long)result);
    pth_kill();

    return (long)result == 42 ? 0 : 1;
}
