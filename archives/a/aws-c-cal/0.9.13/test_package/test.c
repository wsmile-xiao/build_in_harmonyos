#include <stdio.h>
#include <aws/common/common.h>
#include <aws/common/allocator.h>
#include <aws/cal/cal.h>

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    if (allocator == NULL) {
        return 1;
    }
    /* These init functions return void in aws-c-common/aws-c-cal 0.x. */
    aws_common_library_init(allocator);
    aws_cal_library_init(allocator);
    if (aws_error_name(AWS_ERROR_CAL_SIGNATURE_VALIDATION_FAILED) == NULL) {
        aws_cal_library_clean_up();
        aws_common_library_clean_up();
        return 1;
    }
    aws_cal_library_clean_up();
    aws_common_library_clean_up();
    printf("aws-c-cal smoke test OK\n");
    return 0;
}
