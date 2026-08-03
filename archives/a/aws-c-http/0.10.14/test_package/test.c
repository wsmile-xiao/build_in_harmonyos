#include <stdio.h>
#include <string.h>
#include <aws/common/allocator.h>
#include <aws/common/common.h>
#include <aws/cal/cal.h>
#include <aws/compression/compression.h>
#include <aws/http/http.h>
#include <aws/io/io.h>

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    const char *status_text = NULL;
    if (allocator == NULL) {
        return 1;
    }
    aws_common_library_init(allocator);
    aws_cal_library_init(allocator);
    aws_io_library_init(allocator);
    aws_compression_library_init(allocator);
    aws_http_library_init(allocator);
    status_text = aws_http_status_text(200);
    if (status_text == NULL || strcmp(status_text, "OK") != 0) {
        aws_http_library_clean_up();
        aws_compression_library_clean_up();
        aws_io_library_clean_up();
        aws_cal_library_clean_up();
        aws_common_library_clean_up();
        return 1;
    }
    aws_http_library_clean_up();
    aws_compression_library_clean_up();
    aws_io_library_clean_up();
    aws_cal_library_clean_up();
    aws_common_library_clean_up();
    printf("aws-c-http smoke test OK\n");
    return 0;
}
