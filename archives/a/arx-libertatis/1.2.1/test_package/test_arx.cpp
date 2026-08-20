#include <cstdio>
#include <cstring>
#include "ArxIO.h"

int main(void) {
    // ArxIO_init() returns void — verify it doesn't crash
    ArxIO_init();

    // ArxIO_getError() returns void — verify buffer is accessible and null-terminated
    char error_buf[256] = {0};
    ArxIO_getError(error_buf, sizeof(error_buf));
    if (error_buf[255] != 0) {
        fprintf(stderr, "FAIL: ArxIO_getError did not null-terminate\n");
        return 1;
    }

    // ArxIO_getLogLine() returns int — check return value (0 = no log line, >0 = success)
    char log_buf[256] = {0};
    int log_ret = ArxIO_getLogLine(log_buf, sizeof(log_buf));
    if (log_ret < 0) {
        fprintf(stderr, "FAIL: ArxIO_getLogLine returned %d\n", log_ret);
        return 1;
    }

    // ArxIO_unpack_alloc() returns void — verify output buffer behavior
    char *out_buf = nullptr;
    size_t out_size = 0;
    ArxIO_unpack_alloc("", 0, &out_buf, &out_size);
    // With empty input, out_buf may or may not be set — just ensure no crash
    if (out_buf) {
        ArxIO_unpack_free(out_buf);
    }

    // Verify library loaded and all API entry points are callable
    printf("arx-libertatis ArxIO API test: OK\n");
    return 0;
}
