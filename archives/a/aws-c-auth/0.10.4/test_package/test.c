#include <aws/auth/auth.h>
#include <aws/common/allocator.h>

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    aws_auth_library_init(allocator);
    aws_auth_library_clean_up();
    return 0;
}
