#include <stdio.h>
#include <string.h>
#include <aws/common/allocator.h>
#include <aws/common/common.h>
#include <aws/cal/cal.h>
#include <aws/compression/compression.h>
#include <aws/http/http.h>
#include <aws/io/io.h>

static int fail_after_common(void) {
    aws_common_library_clean_up();
    return 1;
}

static int fail_after_cal(void) {
    aws_cal_library_clean_up();
    return fail_after_common();
}

static int fail_after_io(void) {
    aws_io_library_clean_up();
    return fail_after_cal();
}

static int fail_after_compression(void) {
    aws_compression_library_clean_up();
    return fail_after_io();
}

static int fail_after_http(void) {
    aws_http_library_clean_up();
    return fail_after_compression();
}

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    const char *status_text = NULL;
    if (allocator == NULL) {
        return 1;
    }
    if (aws_common_library_init(allocator) != 0) {
        return 1;
    }
    if (aws_cal_library_init(allocator) != 0) {
        return fail_after_common();
    }
    if (aws_io_library_init(allocator) != 0) {
        return fail_after_cal();
    }
    if (aws_compression_library_init(allocator) != 0) {
        return fail_after_io();
    }
    if (aws_http_library_init(allocator) != 0) {
        return fail_after_compression();
    }
    status_text = aws_http_status_text(200);
    if (status_text == NULL || strcmp(status_text, "OK") != 0) {
        return fail_after_http();
    }
    aws_http_library_clean_up();
    aws_compression_library_clean_up();
    aws_io_library_clean_up();
    aws_cal_library_clean_up();
    aws_common_library_clean_up();
    printf("aws-c-http smoke test OK\n");
    return 0;
}
