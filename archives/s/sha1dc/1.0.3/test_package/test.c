#include <stddef.h>
#include <stdio.h>
#include <string.h>

#include <sha1dc/sha1.h>

static void to_hex(const unsigned char digest[20], char out[41]) {
    static const char hex[] = "0123456789abcdef";
    int i;
    for (i = 0; i < 20; ++i) {
        out[i * 2] = hex[digest[i] >> 4];
        out[i * 2 + 1] = hex[digest[i] & 0x0f];
    }
    out[40] = '\0';
}

int main(void) {
    static const char message[] = "abc";
    static const char expected[] = "a9993e364706816aba3e25717850c26c9cd0d89d";
    SHA1_CTX ctx;
    unsigned char digest[20];
    char actual[41];
    int collision;

    SHA1DCInit(&ctx);
    SHA1DCUpdate(&ctx, message, strlen(message));
    collision = SHA1DCFinal(digest, &ctx);
    to_hex(digest, actual);

    if (collision != 0) {
        fprintf(stderr, "Unexpected collision flag for simple SHA-1 input\n");
        return 1;
    }
    if (strcmp(actual, expected) != 0) {
        fprintf(stderr, "Unexpected SHA-1 digest: %s\n", actual);
        return 1;
    }

    printf("sha1dc digest for abc: %s\n", actual);
    return 0;
}
