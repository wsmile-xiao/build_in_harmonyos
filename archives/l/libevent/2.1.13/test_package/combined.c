#include <event2/buffer.h>

#include <stdio.h>
#include <string.h>

int main(void) {
    static const char payload[] = "abc";
    char copied[sizeof(payload)] = {0};
    struct evbuffer *buffer = evbuffer_new();
    if (buffer == NULL) {
        fprintf(stderr, "evbuffer_new failed\n");
        return 1;
    }
    if (evbuffer_add(buffer, payload, sizeof(payload) - 1) != 0) {
        fprintf(stderr, "evbuffer_add failed\n");
        evbuffer_free(buffer);
        return 2;
    }
    if (evbuffer_get_length(buffer) != sizeof(payload) - 1) {
        fprintf(stderr, "unexpected buffer length\n");
        evbuffer_free(buffer);
        return 3;
    }
    if (evbuffer_copyout(buffer, copied, sizeof(payload) - 1) !=
            (int)(sizeof(payload) - 1) ||
        memcmp(copied, payload, sizeof(payload) - 1) != 0) {
        fprintf(stderr, "evbuffer_copyout failed\n");
        evbuffer_free(buffer);
        return 4;
    }
    if (evbuffer_drain(buffer, sizeof(payload) - 1) != 0 ||
        evbuffer_get_length(buffer) != 0) {
        fprintf(stderr, "evbuffer_drain failed\n");
        evbuffer_free(buffer);
        return 5;
    }
    evbuffer_free(buffer);
    puts("libevent combined consumer: OK");
    return 0;
}
