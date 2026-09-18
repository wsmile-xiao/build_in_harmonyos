#include <randombytes.h>
#include <stdio.h>
#include <string.h>
int main(void) {
    unsigned char buf[64];
    memset(buf, 0, sizeof buf);
    randombytes(buf, sizeof buf);
    const char *src = randombytes_source();
    int nonzero = 0;
    for (int i = 0; i < 64; i++) if (buf[i]) nonzero = 1;
    if (!src || !src[0] || !nonzero) {
        fprintf(stderr, "randombytes failed src=%s\n", src ? src : "(null)");
        return 1;
    }
    printf("randombytes source=%s ok\n", src);
    return 0;
}
