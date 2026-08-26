#include <stdio.h>
#include <astrometry/bl.h>

int main(void) {
    bl list;
    bl_init(&list, 8, sizeof(int));
    int val = 42;
    void* result = bl_push(&list, &val);
    if (result) {
        printf("astrometry.net bl_init/bl_push: OK\n");
        /* 栈对象: 用 bl_remove_all 释放内部缓冲；bl_free 会 free(list)（非法用于栈对象） */
        bl_remove_all(&list);
        return 0;
    }
    printf("FAIL: bl_push returned NULL\n");
    return 1;
}
