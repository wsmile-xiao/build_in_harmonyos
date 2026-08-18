#include <aws/io/io.h>
#include <aws/common/allocator.h>

int main(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    aws_io_library_init(allocator);
    aws_io_library_clean_up();
    return 0;
}
