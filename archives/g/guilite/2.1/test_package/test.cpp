// test_package consumer test for guilite 2.1
// Exercises the real public API of the installed package:
//   c_rect / c_fifo / get_time_in_second / second_to_day / build_bmp
// Only uses installed public headers (core_include/api.h) and links libGuiLite.
#include "core_include/api.h"

#include <cstdio>
#include <cstring>

int main() {
    // --- c_rect public API ---
    c_rect rect(0, 0, 100, 50);
    if (rect.width() != 100 || rect.height() != 50) {
        printf("FAIL: c_rect size mismatch\n");
        return 1;
    }
    if (!rect.pt_in_rect(50, 25) || rect.pt_in_rect(200, 200)) {
        printf("FAIL: c_rect pt_in_rect\n");
        return 2;
    }

    // --- c_fifo public API (read/write roundtrip) ---
    c_fifo fifo;
    const char msg[] = "guilite-fifo";
    if (fifo.write((void*)msg, (int)sizeof(msg)) != (int)sizeof(msg)) {
        printf("FAIL: c_fifo write\n");
        return 3;
    }
    char buf[64] = {0};
    if (fifo.read(buf, (int)sizeof(msg)) != (int)sizeof(msg)) {
        printf("FAIL: c_fifo read\n");
        return 4;
    }
    if (strcmp(buf, msg) != 0) {
        printf("FAIL: c_fifo roundtrip mismatch: %s\n", buf);
        return 5;
    }

    // --- time public API ---
    long sec = get_time_in_second();
    if (sec <= 0) {
        printf("FAIL: get_time_in_second\n");
        return 6;
    }
    T_TIME t = second_to_day(sec);
    if (t.year < 2020) {
        printf("FAIL: second_to_day year=%d\n", (int)t.year);
        return 7;
    }

    // --- build_bmp public API: produce a real BMP artifact ---
    // Upstream writes a 16-bit RGB565 BMP: width*height*2 pixel bytes + headers.
    unsigned char pixels[16 * 16 * 4];
    memset(pixels, 0xFF, sizeof(pixels));
    if (build_bmp("guilite-test.bmp", 16, 16, pixels) != 0) {
        printf("FAIL: build_bmp\n");
        return 8;
    }
    FILE* f = fopen("guilite-test.bmp", "rb");
    if (!f) {
        printf("FAIL: guilite-test.bmp not created\n");
        return 9;
    }
    fseek(f, 0, SEEK_END);
    long bmp_size = ftell(f);
    rewind(f);
    unsigned char magic[2] = {0};
    size_t rd = fread(magic, 1, 2, f);
    fclose(f);
    if (bmp_size < 500 || rd != 2 || magic[0] != 'B' || magic[1] != 'M') {
        printf("FAIL: bmp invalid size=%ld magic=%c%c\n", bmp_size, magic[0], magic[1]);
        return 10;
    }

    printf("test guilite 2.1: OK (c_rect/c_fifo/time/build_bmp, bmp=%ld bytes)\n", bmp_size);
    return 0;
}
