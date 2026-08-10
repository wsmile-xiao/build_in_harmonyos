#include <brunsli/decode.h>
#include <brunsli/encode.h>
#include <stdio.h>

/* Dummy sink callback (never called on invalid input) */
static size_t dummy_sink(void *out_data, const unsigned char *buf, size_t size) {
    return size;
}

int main(void) {
    /* Test: DecodeBrunsli with empty input should return 0 (error) */
    unsigned char empty[1] = {0};
    int ret = DecodeBrunsli(0, empty, NULL, dummy_sink);
    if (ret == 0) {
        printf("brunsli v0.1: DecodeBrunsli API test OK\n");
        return 0;
    }
    printf("brunsli v0.1: unexpected return %d\n", ret);
    return 1;
}
