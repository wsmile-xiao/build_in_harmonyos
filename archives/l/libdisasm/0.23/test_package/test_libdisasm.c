/* Consumer test for libdisasm: exercises the public API of the packaged
 * library with hand-verified IA-32 encodings (independent of the host
 * architecture -- the library decodes byte buffers, it never executes them).
 */
#include <stdio.h>
#include <string.h>
#include <libdis.h>

static int failures = 0;
static int checks = 0;

static void check(const char *what, int cond)
{
    checks++;
    if (cond) {
        printf("ok: %s\n", what);
    } else {
        failures++;
        printf("FAIL: %s\n", what);
    }
}

int main(void)
{
    x86_insn_t insn;
    char buf[512];
    size_t i;

    check("x86_init(opt_none) returns 1", x86_init(opt_none, NULL, NULL) == 1);

    /* push ebp : 55 */
    {
        unsigned char b[] = { 0x55 };
        unsigned int sz = x86_disasm(b, sizeof(b), 0, 0, &insn);
        check("push ebp consumes 1 byte", sz == 1);
        check("push ebp type is insn_push", insn.type == insn_push);
        x86_format_insn(&insn, buf, sizeof(buf), intel_syntax);
        /* libdisasm separates the mnemonic from operands with a tab */
        check("push ebp intel text is 'push\\tebp'",
              strncmp(buf, "push\tebp", 8) == 0);
        check("push ebp operand is register ebp",
              x86_operand_1st(&insn)->type == op_register &&
              strcmp(x86_operand_1st(&insn)->data.reg.name, "ebp") == 0);
        x86_oplist_free(&insn);
    }

    /* nop : 90 */
    {
        unsigned char b[] = { 0x90 };
        unsigned int sz = x86_disasm(b, sizeof(b), 0, 0, &insn);
        check("nop consumes 1 byte", sz == 1);
        check("nop type is insn_nop", insn.type == insn_nop);
        x86_format_insn(&insn, buf, sizeof(buf), intel_syntax);
        check("nop intel text is 'nop'", strncmp(buf, "nop", 3) == 0);
        x86_oplist_free(&insn);
    }

    /* mov eax, 1 : B8 01000000 */
    {
        unsigned char b[] = { 0xB8, 0x01, 0x00, 0x00, 0x00 };
        unsigned int sz = x86_disasm(b, sizeof(b), 0, 0, &insn);
        check("mov eax,1 consumes 5 bytes", sz == 5);
        check("mov eax,1 type is insn_mov", insn.type == insn_mov);
        check("mov eax,1 has 2 explicit operands",
              x86_operand_count(&insn, op_explicit) == 2);
        check("mov eax,1 destination is eax",
              x86_operand_1st(&insn)->type == op_register &&
              strcmp(x86_operand_1st(&insn)->data.reg.name, "eax") == 0);
        check("mov eax,1 source is immediate 1",
              x86_operand_2nd(&insn)->type == op_immediate &&
              x86_operand_2nd(&insn)->data.dword == 1);
        x86_oplist_free(&insn);
    }

    /* add eax, ebx : 03 C3 */
    {
        unsigned char b[] = { 0x03, 0xC3 };
        unsigned int sz = x86_disasm(b, sizeof(b), 0, 0, &insn);
        check("add eax,ebx consumes 2 bytes", sz == 2);
        check("add eax,ebx type is insn_add", insn.type == insn_add);
        x86_format_insn(&insn, buf, sizeof(buf), intel_syntax);
        check("add eax,ebx intel text starts with 'add\\teax'",
              strncmp(buf, "add\teax", 7) == 0);
        x86_oplist_free(&insn);
    }

    /* Walk a small function prologue+epilogue stream:
     *   55        push ebp
     *   8B EC     mov ebp, esp
     *   83 EC 08  sub esp, 8
     *   90        nop
     *   C3        ret
     */
    {
        unsigned char code[] = { 0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x08,
                                 0x90, 0xC3 };
        static const unsigned int sizes[]  = { 1, 2, 3, 1, 1 };
        static const enum x86_insn_type types[] = {
            insn_push, insn_mov, insn_sub, insn_nop, insn_return
        };
        int all_ok = 1;
        i = 0;
        while (i < sizeof(code)) {
            unsigned int sz = x86_disasm(code, sizeof(code), 0, i, &insn);
            if (sz == 0) {
                printf("FAIL: stream broke at offset %u\n", (unsigned int)i);
                all_ok = 0;
                break;
            }
            x86_oplist_free(&insn);
            i += sz;
        }
        check("prologue stream disassembles to the end", i == sizeof(code));
        i = 0;
        for (int n = 0; n < 5; n++) {
            unsigned int sz = x86_disasm(code, sizeof(code), 0, i, &insn);
            if (sz != sizes[n] || insn.type != types[n]) {
                printf("FAIL: insn %d at offset %u: sz=%u type=0x%X "
                       "(want %u/0x%X)\n", n, (unsigned int)i, sz, insn.type,
                       sizes[n], types[n]);
                all_ok = 0;
            }
            x86_oplist_free(&insn);
            i += sizes[n];
        }
        check("every instruction in the stream has the expected size and type",
              all_ok);
    }

    /* Invalid opcode pair (0F 38 escape is incomplete in the 0.23 tables):
     * the library must report 0 bytes and insn_invalid. */
    {
        unsigned char b[] = { 0x0F, 0x38 };
        unsigned int sz = x86_disasm(b, sizeof(b), 0, 0, &insn);
        check("0F 38 reports no valid instruction", sz == 0);
        check("0F 38 is typed insn_invalid", insn.type == insn_invalid);
        x86_oplist_free(&insn);
    }

    check("x86_cleanup() returns 1", x86_cleanup() == 1);

    printf("%d/%d assertions passed\n", checks - failures, checks);
    return failures ? 1 : 0;
}
