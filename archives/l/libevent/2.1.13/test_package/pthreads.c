#include <event2/event.h>
#include <event2/thread.h>

#include <stdio.h>

int main(void) {
    if (evthread_use_pthreads() != 0) {
        fprintf(stderr, "evthread_use_pthreads failed\n");
        return 1;
    }

    struct event_base *base = event_base_new();
    if (base == NULL) {
        fprintf(stderr, "event_base_new failed\n");
        return 2;
    }
    if (event_base_get_method(base) == NULL) {
        fprintf(stderr, "event_base_get_method returned NULL\n");
        event_base_free(base);
        return 3;
    }
    event_base_free(base);
    puts("libevent pthreads consumer: OK");
    return 0;
}
