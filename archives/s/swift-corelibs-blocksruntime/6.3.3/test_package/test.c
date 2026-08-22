#include <Block_private.h>
#include <stdio.h>

int main(void)
{
    int captured = 42;
    int (^stack_block)(void) = ^{ return captured; };
    int (^heap_block)(void) = Block_copy(stack_block);
    size_t stack_size = Block_size((void *)stack_block);
    size_t heap_size = Block_size((void *)heap_block);
    int has_signature = _Block_has_signature((void *)heap_block);
    const char *signature = _Block_signature((void *)heap_block);

    Block_release(heap_block);
    if (stack_size == 0 || heap_size != stack_size || !has_signature || signature == NULL) {
        fprintf(stderr,
                "Block metadata invalid: stack_size=%zu heap_size=%zu signature=%d/%p\n",
                stack_size, heap_size, has_signature, (const void *)signature);
        return 1;
    }

    puts("block_metadata: PASS");
    return 0;
}
