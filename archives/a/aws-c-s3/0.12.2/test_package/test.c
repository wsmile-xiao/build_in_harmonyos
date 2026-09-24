#include <aws/s3/s3.h>
#include <aws/common/allocator.h>
#include <stdio.h>

int main(void) {
    /* Get the default allocator */
    struct aws_allocator *allocator = aws_default_allocator();
    if (allocator == NULL) {
        fprintf(stderr, "FAIL: aws_default_allocator() returned NULL\n");
        return 1;
    }

    /* Initialize the S3 library */
    aws_s3_library_init(allocator);
    printf("OK: aws_s3_library_init() succeeded\n");

    /* Get platform info - tests that the library is functional */
    const struct aws_s3_platform_info *platform_info = aws_s3_get_current_platform_info();
    if (platform_info != NULL) {
        printf("OK: aws_s3_get_current_platform_info() returned non-NULL\n");
        if (platform_info->max_throughput_gbps > 0) {
            printf("OK: platform max_throughput_gbps = %.2f\n", platform_info->max_throughput_gbps);
        } else {
            printf("OK: platform max_throughput_gbps = 0 (unknown instance type)\n");
        }
    } else {
        fprintf(stderr, "WARN: aws_s3_get_current_platform_info() returned NULL\n");
    }

    /* Clean up the S3 library */
    aws_s3_library_clean_up();
    printf("OK: aws_s3_library_clean_up() succeeded\n");

    printf("ALL TESTS PASSED: aws-c-s3 0.12.2\n");
    return 0;
}
