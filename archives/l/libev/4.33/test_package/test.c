#include <stdio.h>
#include <ev.h>

int main(void) {
    printf("libev version: %d.%d\n", ev_version_major(), ev_version_minor());

    struct ev_loop *loop = ev_default_loop(0);
    if (!loop) {
        fprintf(stderr, "Failed to create default loop\n");
        return 1;
    }
    printf("Default loop created successfully\n");

    ev_loop_destroy(loop);
    printf("Test passed\n");
    return 0;
}
