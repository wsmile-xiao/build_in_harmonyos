#include <aws/common/allocator.h>
#include <aws/common/common.h>
#include <aws/sdkutils/sdkutils.h>
#include <aws/sdkutils/partitions.h>
#include <stdio.h>

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    if (allocator == NULL) {
        fprintf(stderr, "FAIL: aws_default_allocator() returned NULL\n");
        return 1;
    }

    /* Initialize aws-c-common first (dependency) */
    aws_common_library_init(allocator);

    /* Initialize aws-c-sdkutils */
    aws_sdkutils_library_init(allocator);

    /* Get the supported partitions version and verify it is non-empty */
    struct aws_byte_cursor version = aws_partitions_get_supported_version();
    if (version.len == 0 || version.ptr == NULL) {
        fprintf(stderr, "FAIL: aws_partitions_get_supported_version returned empty\n");
        aws_sdkutils_library_clean_up();
        aws_common_library_clean_up();
        return 1;
    }

    /* Print the version string for verification */
    printf("aws_partitions_get_supported_version = %.*s\n", (int)version.len, version.ptr);

    /* Clean up */
    aws_sdkutils_library_clean_up();
    aws_common_library_clean_up();

    printf("test aws-c-sdkutils 0.2.7: OK\n");
    return 0;
}
