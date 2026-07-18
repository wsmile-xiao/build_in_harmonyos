#include <stdio.h>
#include <string.h>
#include <aws/common/common.h>
#include <aws/http/http.h>

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    if (allocator == NULL) {
        return 1;
    }
    aws_common_library_init(allocator);
    aws_http_library_init(allocator);

    if (strcmp(aws_http_status_text(200), "OK") != 0) {
        aws_http_library_clean_up();
        aws_common_library_clean_up();
        return 1;
    }

    aws_http_library_clean_up();
    aws_common_library_clean_up();
    printf("aws-c-http smoke test OK\n");
    return 0;
}
