#include <libp11.h>

int main(void) {
    PKCS11_CTX *ctx = PKCS11_CTX_new();
    if (ctx == NULL) {
        return 1;
    }
    PKCS11_CTX_free(ctx);
    return 0;
}
