#include <Block.h>
#include <stdio.h>

typedef int (^IntBlock)(void);

static IntBlock make_block(int value)
{
    IntBlock stack_block = ^{ return value; };
    return Block_copy(stack_block);
}

int main(void)
{
    IntBlock escaped_block = make_block(42);
    int result = escaped_block();

    Block_release(escaped_block);
    if (result != 42) {
        fprintf(stderr, "Escaped Block returned %d instead of 42\n", result);
        return 1;
    }

    puts("escape_lifetime: PASS");
    return 0;
}
