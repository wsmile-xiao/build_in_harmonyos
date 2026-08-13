#include <wolfssl/ssl.h>
#include <stdio.h>

int main(void) {
    if (wolfSSL_Init() != SSL_SUCCESS) {
        fprintf(stderr, "wolfSSL_Init failed\n");
        return 1;
    }
    printf("wolfSSL version: %s\n", wolfSSL_lib_version());
    wolfSSL_Cleanup();
    return 0;
}
