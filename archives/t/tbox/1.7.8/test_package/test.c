#include <stdio.h>
#include <string.h>

#include "tbox/tbox.h"

int main(void) {
    tb_char_t buf[16] = {0};
    tb_long_t n;

    if (!tb_init(tb_null, tb_null)) {
        fprintf(stderr, "tb_init failed\n");
        return 1;
    }

    /* Real API assertions against the compiled tbox library. */
    n = tb_snprintf(buf, sizeof(buf), "%u+%s", 4096, "tbox");
    if (n != 9 || tb_strcmp(buf, "4096+tbox") != 0) {
        fprintf(stderr, "tb_snprintf round-trip mismatch: %s\n", buf);
        tb_exit();
        return 2;
    }

    /* Core allocator round-trip (small-mode build: memory ops are core). */
    tb_byte_t* p = (tb_byte_t*)tb_malloc(32);
    if (!p) {
        fprintf(stderr, "tb_malloc failed\n");
        tb_exit();
        return 3;
    }
    tb_memset(p, 0xA5, 32);
    if (p[0] != 0xA5 || p[31] != 0xA5) {
        fprintf(stderr, "tb_memset/tb_malloc mismatch\n");
        tb_free(p);
        tb_exit();
        return 3;
    }
    tb_free(p);

    tb_exit();
    puts("tbox API assertions: 3 passed");
    return 0;
}
