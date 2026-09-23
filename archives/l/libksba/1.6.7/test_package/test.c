#include <ksba.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    const char *version = ksba_check_version(NULL);
    ksba_cert_t cert = NULL;

    if (!version || strcmp(version, KSBA_VERSION) != 0) {
        fprintf(stderr, "unexpected libksba version: %s\n", version ? version : "null");
        return 1;
    }
    if (ksba_cert_new(&cert) != 0 || cert == NULL) {
        fprintf(stderr, "ksba_cert_new failed\n");
        return 2;
    }
    ksba_cert_release(cert);
    printf("libksba consumer test: %s\n", version);
    return 0;
}
