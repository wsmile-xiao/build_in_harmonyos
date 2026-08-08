#include <aws/common/common.h>
#include <aws/common/allocator.h>
#include <aws/common/string.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    /* Initialize the aws-c-common library with the default allocator */
    struct aws_allocator *allocator = aws_default_allocator();
    aws_common_library_init(allocator);

    /* Create a string and verify its contents */
    const char *test_str = "Hello, OHOS!";
    struct aws_string *str = aws_string_new_from_c_str(allocator, test_str);
    if (str == NULL) {
        fprintf(stderr, "FAIL: aws_string_new_from_c_str returned NULL\n");
        aws_common_library_clean_up();
        return 1;
    }

    const uint8_t *bytes = aws_string_bytes(str);
    if (bytes == NULL) {
        fprintf(stderr, "FAIL: aws_string_bytes returned NULL\n");
        aws_string_destroy(str);
        aws_common_library_clean_up();
        return 1;
    }

    /* Verify the string content matches */
    size_t expected_len = strlen(test_str);
    if (aws_string_is_valid(str) == 0) {
        fprintf(stderr, "FAIL: aws_string_is_valid returned false\n");
        aws_string_destroy(str);
        aws_common_library_clean_up();
        return 1;
    }

    if (str->len != expected_len) {
        fprintf(stderr, "FAIL: string length mismatch: got %zu, expected %zu\n",
                str->len, expected_len);
        aws_string_destroy(str);
        aws_common_library_clean_up();
        return 1;
    }

    if (memcmp(bytes, test_str, expected_len) != 0) {
        fprintf(stderr, "FAIL: string content mismatch\n");
        aws_string_destroy(str);
        aws_common_library_clean_up();
        return 1;
    }

    printf("PASS: aws-c-common string API works correctly (len=%zu, str=%s)\n",
           str->len, (const char *)bytes);

    aws_string_destroy(str);
    aws_common_library_clean_up();

    printf("PASS: aws-c-common 0.14.3 test completed successfully\n");
    return 0;
}
