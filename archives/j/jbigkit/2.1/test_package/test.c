/* test_package/test.c — jbigkit 2.1 链接 + 真实符号调用 (R34) */
#include <stdio.h>
#include "jbig.h"

int main(void) {
    struct jbg_dec_state s;
    jbg_dec_init(&s);        /* 调用 libjbig 导出符号，证明库可用 */
    jbg_dec_free(&s);
    printf("jbigkit: jbg_dec_init/free ok\n");
    return 0;
}
