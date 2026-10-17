#include <zmq.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    int major, minor, patch;
    zmq_version(&major, &minor, &patch);
    printf("ZeroMQ version: %d.%d.%d\n", major, minor, patch);

    void *ctx = zmq_ctx_new();
    if (!ctx) {
        fprintf(stderr, "Failed to create ZMQ context\n");
        return 1;
    }

    void *sock = zmq_socket(ctx, ZMQ_REP);
    if (!sock) {
        fprintf(stderr, "Failed to create ZMQ socket\n");
        zmq_ctx_term(ctx);
        return 1;
    }

    int rc = zmq_bind(sock, "inproc://test");
    if (rc != 0) {
        fprintf(stderr, "Failed to bind ZMQ socket\n");
        zmq_close(sock);
        zmq_ctx_term(ctx);
        return 1;
    }

    printf("ZMQ socket bound successfully\n");
    zmq_close(sock);
    zmq_ctx_term(ctx);
    printf("All tests passed!\n");
    return 0;
}
