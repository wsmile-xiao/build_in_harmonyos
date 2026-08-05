#include <stdio.h>

/* Forward-declare the aws-c-cal API to avoid needing aws-c-common headers.
 * The test verifies that libaws-c-cal.a links correctly and the library
 * functions are callable. */
struct aws_allocator;
extern void aws_cal_library_init(struct aws_allocator *allocator);
extern void aws_cal_library_clean_up(void);

int main(void) {
    /* Initialize and clean up the cal library.
     * Pass NULL allocator — aws_common_library_init handles this gracefully
     * by falling back to the default allocator. */
    aws_cal_library_init((void *)0);
    printf("aws-c-cal library initialized: OK\n");
    aws_cal_library_clean_up();
    printf("aws-c-cal library cleaned up: OK\n");
    return 0;
}
