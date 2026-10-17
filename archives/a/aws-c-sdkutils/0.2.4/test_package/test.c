#include <stdio.h>

/* Forward-declare the aws-c-sdkutils API to avoid needing aws-c-common headers.
 * The test verifies that libaws-c-sdkutils links correctly and the library
 * functions are callable.
 * Mirrors upstream test: tests/sdkutils_test.c (sdkutils_library_test)
 */
struct aws_allocator;
extern void aws_sdkutils_library_init(struct aws_allocator *allocator);
extern void aws_sdkutils_library_clean_up(void);

int main(void) {
    /* Initialize and clean up the sdkutils library.
     * Pass NULL allocator — the library falls back to the default allocator. */
    aws_sdkutils_library_init((void *)0);
    printf("aws-c-sdkutils library initialized: OK\n");
    aws_sdkutils_library_clean_up();
    printf("aws-c-sdkutils library cleaned up: OK\n");
    return 0;
}
