#include <stdio.h>
#include <stdlib.h>
#include <oggz/oggz.h>

int main(void) {
    /* 真实调用被测包 API：创建 OGGZ 读句柄并关闭（R34 禁空壳） */
    OGGZ *oggz = oggz_new(OGGZ_READ);
    if (oggz == NULL) {
        fprintf(stderr, "liboggz: oggz_new(OGGZ_READ) returned NULL\n");
        return 1;
    }
    if (oggz_close(oggz) != 0) {
        fprintf(stderr, "liboggz: oggz_close() failed\n");
        return 1;
    }
    printf("test liboggz 1.1.1: oggz_new/oggz_close OK\n");
    return 0;
}