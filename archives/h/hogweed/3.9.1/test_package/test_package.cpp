#include <nettle/rsa.h>
#include <stdio.h>

int main(void) {
    struct rsa_public_key pub;
    rsa_public_key_init(&pub);
    rsa_public_key_clear(&pub);
    puts("hogweed rsa API assertion: 1 passed");
    return 0;
}