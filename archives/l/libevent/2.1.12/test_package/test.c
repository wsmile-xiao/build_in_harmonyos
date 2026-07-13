#include <stdio.h>
#include <stdlib.h>
#include <event2/event.h>

int main(void) {
    /* Verify libevent is linkable and the version string is accessible */
    const char *ver = event_get_version();
    printf("libevent version: %s\n", ver);

    /* Basic event base creation/free to verify API works */
    struct event_base *base = event_base_new();
    if (base == NULL) {
        fprintf(stderr, "Could not initialize libevent!\n");
        return 1;
    }
    event_base_free(base);
    printf("test libevent 2.1.12: OK\n");
    return 0;
}
