#include <Block.h>
#include <stdio.h>

int main(void)
{
    int (^global_block)(int) = ^(int value) { return value * 2; };
    int (^copied_block)(int) = Block_copy(global_block);
    int result = copied_block(21);

    Block_release(copied_block);
    if (result != 42) {
        fprintf(stderr, "Global Block returned %d instead of 42\n", result);
        return 1;
    }

    puts("global_block: PASS");
    return 0;
}
