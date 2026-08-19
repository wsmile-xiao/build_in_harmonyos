#include <stdio.h>
#include <string.h>
#include <libnet.h>

int main(void) {
    char err_buf[LIBNET_ERRBUF_SIZE];
    /* R34: Call libnet API — initialize a context with LIBNET_NONE
     * (no injection, just packet construction) */
    libnet_t *l = libnet_init(LIBNET_NONE, NULL, err_buf);
    if (l == NULL) {
        fprintf(stderr, "libnet_init() failed: %s\n", err_buf);
        return 1;
    }

    /* Print the version to verify the library is properly linked */
    printf("libnet version: %s\n", libnet_version());

    /* Clean up */
    libnet_destroy(l);
    printf("libnet test: OK\n");
    return 0;
}
