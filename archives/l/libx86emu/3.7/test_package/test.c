/*
 * libx86emu 3.7 — real functional smoke test (R34)
 *
 * 加载一小段真实 x86 机器码（mov ax,0x1234; hlt）到模拟内存，
 * 经 libx86emu 执行后校验寄存器结果，证明库的指令模拟真实可用。
 */
#include <stdio.h>
#include <string.h>
#include "x86emu.h"

static int on_intr(x86emu_t *emu, u8 num, unsigned type)
{
    if ((type & 0xff) == INTR_TYPE_FAULT) {
        x86emu_stop(emu);
    }
    return 0;
}

int main(void)
{
    /* B8 34 12 = mov ax, 0x1234 ; F4 = hlt */
    static const u8 code[] = { 0xB8, 0x34, 0x12, 0xF4 };
    x86emu_t *emu;
    unsigned i;

    emu = x86emu_new(X86EMU_PERM_R | X86EMU_PERM_W | X86EMU_PERM_X, 0);
    if (!emu) {
        fprintf(stderr, "FAIL: x86emu_new returned NULL\n");
        return 1;
    }

    x86emu_set_intr_handler(emu, on_intr);

    /* 实模式平面地址：cs=0x0000，ip=0x0100 -> 物理 0x0100 */
    emu->x86.R_CS = 0x0000;
    emu->x86.R_CS_BASE = 0x00000;
    emu->x86.R_DS = 0x0000;
    emu->x86.R_DS_BASE = 0x00000;
    emu->x86.R_ES = 0x0000;
    emu->x86.R_ES_BASE = 0x00000;
    emu->x86.R_SS = 0x0000;
    emu->x86.R_SS_BASE = 0x00000;
    emu->x86.R_EIP = 0x0100;

    for (i = 0; i < sizeof(code); i++) {
        x86emu_write_byte(emu, 0x0100 + i, code[i]);
    }

    emu->max_instr = 8;
    x86emu_run(emu, X86EMU_RUN_LOOP | X86EMU_RUN_NO_CODE | X86EMU_RUN_MAX_INSTR);

    printf("libx86emu functional test: R_AX=0x%04x (expected 0x1234)\n",
           emu->x86.R_AX);

    if (emu->x86.R_AX != 0x1234) {
        fprintf(stderr, "FAIL: R_AX mismatch, emulation did not execute mov ax,0x1234\n");
        x86emu_done(emu);
        return 1;
    }

    x86emu_done(emu);
    printf("PASS: x86emu executed mov ax,0x1234 and hlt correctly\n");
    return 0;
}
