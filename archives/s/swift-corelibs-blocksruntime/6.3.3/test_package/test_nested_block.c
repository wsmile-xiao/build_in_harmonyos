#include <Block.h>
#include <stdio.h>

int main(void)
{
    int offset = 1;
    int (^inner_block)(int) = ^(int value) { return value * 2; };
    int (^stack_outer)(int) = ^(int value) { return inner_block(value) + offset; };
    int (^heap_outer)(int) = Block_copy(stack_outer);
    int result = heap_outer(20) + 1;

    Block_release(heap_outer);
    if (result != 42) {
        fprintf(stderr, "Nested Block returned %d instead of 42\n", result);
        return 1;
    }

    puts("nested_block: PASS");
    return 0;
}
