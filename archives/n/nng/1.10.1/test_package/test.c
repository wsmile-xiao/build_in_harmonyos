#include <nng/nng.h>
#include <nng/protocol/pair0/pair.h>
#include <stdio.h>

int main(void)
{
    nng_socket socket;
    int rv = nng_pair0_open(&socket);
    if (rv != 0) {
        fprintf(stderr, "nng_pair0_open: %s\n", nng_strerror(rv));
        return 1;
    }

    rv = nng_close(socket);
    if (rv != 0) {
        fprintf(stderr, "nng_close: %s\n", nng_strerror(rv));
        return 1;
    }

    printf("NNG %s pair0 API smoke test passed\n", nng_version());
    return 0;
}
