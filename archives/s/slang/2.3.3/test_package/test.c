#include <stdio.h>
#include <stdlib.h>
#include <slang.h>

int main(void) {
    /* Initialize the S-Lang library */
    int ret = SLang_init_all();
    if (ret == -1) {
        fprintf(stderr, "SLang_init_all() failed\n");
        return 1;
    }
    printf("test slang 2.3.3: OK (SLang_init_all returned %d)\n", ret);
    return 0;
}
