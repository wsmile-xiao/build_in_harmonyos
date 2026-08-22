#include <Block.h>
#include <stdio.h>

int main(void)
{
    int captured = 21;
    int (^stack_block)(void) = ^{ return captured * 2; };
    int (^first_copy)(void) = Block_copy(stack_block);
    int (^second_copy)(void) = Block_copy(first_copy);
    int first_result = first_copy();

    Block_release(first_copy);
    int second_result = second_copy();
    Block_release(second_copy);

    if (first_result != 42 || second_result != 42) {
        fprintf(stderr, "Retained Block returned %d and %d instead of 42\n",
                first_result, second_result);
        return 1;
    }

    puts("retain_release: PASS");
    return 0;
}
