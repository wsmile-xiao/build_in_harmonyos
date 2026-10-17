#include <stdio.h>
#include <stdlib.h>

#include <libuv/uv.h>

int main(void) {
    int mask_size = uv_cpumask_size();
    if (mask_size <= 0) {
        fprintf(stderr, "uv_cpumask_size failed: %d\n", mask_size);
        return 1;
    }

    char *current = calloc((size_t)mask_size, 1);
    char *requested = calloc((size_t)mask_size, 1);
    char *previous = calloc((size_t)mask_size, 1);
    char *observed = calloc((size_t)mask_size, 1);
    if (!current || !requested || !previous || !observed) {
        return 2;
    }

    uv_thread_t thread = uv_thread_self();
    int result = uv_thread_getaffinity(&thread, current, (size_t)mask_size);
    if (result != 0) {
        fprintf(stderr, "uv_thread_getaffinity failed: %s\n", uv_strerror(result));
        return 3;
    }

    int selected_cpu = -1;
    for (int cpu = 0; cpu < mask_size; ++cpu) {
        if (current[cpu]) {
            selected_cpu = cpu;
            requested[cpu] = 1;
            break;
        }
    }
    if (selected_cpu < 0) {
        fprintf(stderr, "current affinity mask is empty\n");
        return 4;
    }

    result = uv_thread_setaffinity(
        &thread, requested, previous, (size_t)mask_size
    );
    if (result != 0) {
        fprintf(stderr, "uv_thread_setaffinity failed: %s\n", uv_strerror(result));
        return 5;
    }

    result = uv_thread_getaffinity(&thread, observed, (size_t)mask_size);
    if (result != 0 || !observed[selected_cpu]) {
        fprintf(stderr, "updated affinity mask was not observed\n");
        return 6;
    }

    result = uv_thread_setaffinity(
        &thread, previous, NULL, (size_t)mask_size
    );
    if (result != 0) {
        fprintf(stderr, "failed to restore affinity: %s\n", uv_strerror(result));
        return 7;
    }

    printf("libuv affinity round trip passed on CPU %d\n", selected_cpu);
    free(current);
    free(requested);
    free(previous);
    free(observed);
    return 0;
}
