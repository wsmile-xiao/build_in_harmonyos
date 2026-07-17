#include <stdio.h>
#include <aws/common/allocator.h>
#include <aws/common/common.h>
#include <aws/http/http.h>

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    if (allocator == NULL) {
        return 1;
    }
    if (aws_common_library_init(allocator) != 0) {
        fprintf(stderr, "aws_common_library_init failed\n");
        return 1;
    }
    if (aws_http_library_init(allocator) != 0) {
        fprintf(stderr, "aws_http_library_init failed\n");
        aws_common_library_clean_up();
        return 1;
    }
    aws_http_library_clean_up();
    aws_common_library_clean_up();
    printf("aws-c-http smoke test OK\n");
    return 0;
}
