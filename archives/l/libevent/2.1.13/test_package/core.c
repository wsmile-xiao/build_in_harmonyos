#include <event2/event.h>

#include <stdio.h>

int main(void) {
    const char *version = event_get_version();
    if (version == NULL) {
        fprintf(stderr, "event_get_version returned NULL\n");
        return 1;
    }
    if (event_get_version_number() != LIBEVENT_VERSION_NUMBER) {
        fprintf(stderr, "header and library versions differ\n");
        return 2;
    }

    struct event_base *base = event_base_new();
    if (base == NULL) {
        fprintf(stderr, "event_base_new failed\n");
        return 3;
    }
    event_base_free(base);
    printf("libevent core consumer: %s\n", version);
    return 0;
}
