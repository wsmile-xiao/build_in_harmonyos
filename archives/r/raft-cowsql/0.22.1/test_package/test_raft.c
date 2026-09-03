#include <raft.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    /* Test raft_strerror with an unknown error code */
    const char *msg = raft_strerror(666);
    if (msg == NULL) {
        fprintf(stderr, "FAIL: raft_strerror(666) returned NULL\n");
        return 1;
    }
    if (strcmp(msg, "unknown error") != 0) {
        fprintf(stderr, "FAIL: raft_strerror(666) returned \"%s\", expected \"unknown error\"\n", msg);
        return 1;
    }
    printf("test raft-cowsql 0.22.1: raft_strerror(666) = \"%s\" -- OK\n", msg);
    return 0;
}
