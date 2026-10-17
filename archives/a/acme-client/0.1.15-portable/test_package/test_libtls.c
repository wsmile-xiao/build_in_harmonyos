#include <stdio.h>
#include <tls.h>

int main(void)
{
    struct tls_config *config = NULL;
    struct tls *client = NULL;

    if (tls_init() != 0) {
        fprintf(stderr, "tls_init failed\n");
        return 1;
    }

    config = tls_config_new();
    if (config == NULL) {
        fprintf(stderr, "tls_config_new failed\n");
        return 2;
    }
    tls_config_free(config);

    client = tls_client();
    if (client == NULL) {
        fprintf(stderr, "tls_client failed\n");
        return 3;
    }

    /* LibreSSL 3.9.1 maps NULL to its reference-counted default config. */
    if (tls_configure(client, NULL) != 0) {
        fprintf(stderr, "tls_configure failed: %s\n", tls_error(client));
        tls_free(client);
        return 4;
    }

    tls_free(client);
    puts("PASS: LibreSSL libtls client initialized and configured");
    return 0;
}
