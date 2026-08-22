#include <Block.h>
#include <stdio.h>

int main(void)
{
    __block int counter = 40;
    void (^stack_block)(void) = ^{ counter += 1; };
    void (^heap_block)(void) = Block_copy(stack_block);

    heap_block();
    heap_block();
    Block_release(heap_block);

    if (counter != 42) {
        fprintf(stderr, "__block capture ended at %d instead of 42\n", counter);
        return 1;
    }

    puts("byref_capture: PASS");
    return 0;
}
