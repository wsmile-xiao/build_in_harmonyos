#include <stdio.h>
#include <stdlib.h>
#include <libdwarf.h>

int main() {
    /* R34: 实质调用被测包 API — 调用 dwarf_init_path() 验证库已正确链接 */
    Dwarf_Debug dbg = 0;
    Dwarf_Error err = 0;

    /* 不打开实际文件（传入 NULL 路径），预期返回 DW_DLV_ERROR
       关键验证点是 dwarf_init_path() 函数符号可解析且调用不崩溃 */
    int res = dwarf_init_path(
        NULL,   /* dw_path: 无实际文件 */
        NULL,   /* dw_true_path_out_buffer */
        0,      /* dw_true_path_bufferlen */
        0,      /* dw_groupnumber */
        NULL,   /* dw_errhand */
        NULL,   /* dw_errarg */
        &dbg,
        &err);

    if (res == DW_DLV_ERROR) {
        /* 无文件时返回 DW_DLV_ERROR 是预期行为，证明库已正确加载 */
        printf("libdwarf: OK (dwarf_init_path loaded)\n");
        return 0;
    } else if (res == DW_DLV_OK) {
        dwarf_finish(dbg);
        printf("libdwarf: OK (dwarf_init_path opened)\n");
        return 0;
    }

    printf("libdwarf: FAILED (res=%d)\n", res);
    return 1;
}
