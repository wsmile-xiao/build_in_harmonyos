#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <raft.h>

int main(void) {
    struct raft_configuration config;
    struct raft_buffer buf;
    int rv;

    /* Test: raft_configuration_init + raft_configuration_add */
    raft_configuration_init(&config);
    rv = raft_configuration_add(&config, 1, "127.0.0.1:9090", RAFT_STANDBY);
    if (rv != 0) {
        fprintf(stderr, "raft_configuration_add failed: %s\n", raft_strerror(rv));
        raft_configuration_close(&config);
        return 1;
        return 1;
        return 1;
    }

    /* Test: raft_configuration_encode */
    rv = raft_configuration_encode(&config, &buf);
    if (rv != 0) {
        fprintf(stderr, "raft_configuration_encode failed: %s\n", raft_strerror(rv));
        raft_configuration_close(&config);
        return 1;
    }
    if (buf.len == 0) {
        fprintf(stderr, "raft_configuration_encode produced empty buffer\n");
        raft_free(buf.base);
        raft_configuration_close(&config);
        return 1;
    }
    raft_free(buf.base);

    raft_configuration_close(&config);

    printf("test raft 0.18.1: OK\n");
    return 0;
}