#include <libyuv/convert_argb.h>
#include <stdio.h>

int main(void) {
    const uint8_t y[4] = {82, 82, 82, 82};
    const uint8_t u[1] = {90};
    const uint8_t v[1] = {240};
    uint8_t argb[16] = {0};
    int rc = I420ToARGB(y, 2, u, 1, v, 1, argb, 8, 2, 2);
    if (rc != 0 || argb[3] != 255 || argb[0] == 0 || argb[1] == 0 || argb[2] == 0) {
        fprintf(stderr, "I420ToARGB failed: rc=%d pixel=%u,%u,%u,%u\n", rc, argb[0], argb[1], argb[2], argb[3]);
        return 1;
    }
    printf("libyuv I420ToARGB smoke test: %u,%u,%u,%u OK\n", argb[0], argb[1], argb[2], argb[3]);
    return 0;
}
