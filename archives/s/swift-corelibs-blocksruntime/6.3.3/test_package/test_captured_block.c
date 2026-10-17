#include <Block.h>
#include <stdio.h>

int main(void)
{
    int captured = 40;
    int (^stack_block)(int) = ^(int value) { return captured + value; };
    int (^heap_block)(int) = Block_copy(stack_block);
    int result = heap_block(2);

    Block_release(heap_block);
    if (result != 42) {
        fprintf(stderr, "Captured-value Block returned %d instead of 42\n", result);
        return 1;
    }

    puts("captured_block: PASS");
    return 0;
}
