#include <stdio.h>
#include <string.h>
#include <aws/common/allocator.h>
#include <aws/common/common.h>
#include <aws/cal/cal.h>
#include <aws/compression/compression.h>
#include <aws/http/http.h>
#include <aws/io/io.h>

#define INIT_LIBRARY(func, allocator) \
    _Generic((func), \
        void (*)(struct aws_allocator *): ((func)(allocator), AWS_OP_SUCCESS), \
        int (*)(struct aws_allocator *): (func)(allocator) \
    )

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    const char *status_text = NULL;
    if (allocator == NULL) {
        return 1;
    }
    if (INIT_LIBRARY(aws_common_library_init, allocator) != AWS_OP_SUCCESS) {
        return 1;
    }
    if (INIT_LIBRARY(aws_cal_library_init, allocator) != AWS_OP_SUCCESS) {
        goto cleanup_common;
    }
    if (INIT_LIBRARY(aws_io_library_init, allocator) != AWS_OP_SUCCESS) {
        goto cleanup_cal;
    }
    if (INIT_LIBRARY(aws_compression_library_init, allocator) != AWS_OP_SUCCESS) {
        goto cleanup_io;
    }
    if (INIT_LIBRARY(aws_http_library_init, allocator) != AWS_OP_SUCCESS) {
        goto cleanup_compression;
    }
    status_text = aws_http_status_text(200);
    if (status_text == NULL || strcmp(status_text, "OK") != 0) {
        aws_http_library_clean_up();
        goto cleanup_compression_with_error;
    }
    aws_http_library_clean_up();
    aws_compression_library_clean_up();
    aws_io_library_clean_up();
    aws_cal_library_clean_up();
    aws_common_library_clean_up();
    printf("aws-c-http smoke test OK\n");
    return 0;

cleanup_compression_with_error:
    aws_compression_library_clean_up();
cleanup_io:
    aws_io_library_clean_up();
cleanup_cal:
    aws_cal_library_clean_up();
cleanup_common:
    aws_common_library_clean_up();
    return 1;

cleanup_compression:
    aws_compression_library_clean_up();
    goto cleanup_io;
}
