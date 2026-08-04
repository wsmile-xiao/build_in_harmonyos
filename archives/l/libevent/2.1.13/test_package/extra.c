#include <event2/event.h>
#include <event2/http.h>

#include <stdio.h>

int main(void) {
    struct event_base *base = event_base_new();
    if (base == NULL) {
        fprintf(stderr, "event_base_new failed\n");
        return 1;
    }

    struct evhttp *http = evhttp_new(base);
    if (http == NULL) {
        fprintf(stderr, "evhttp_new failed\n");
        event_base_free(base);
        return 2;
    }
    evhttp_free(http);
    event_base_free(base);
    puts("libevent extra consumer: OK");
    return 0;
}
