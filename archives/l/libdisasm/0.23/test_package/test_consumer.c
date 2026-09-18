/* Consumer use case for libdisasm 0.23.
 *
 * Emulates what a small binary-inspection tool does: linearly scan an
 * x86 code buffer, list every instruction, and locate the "write
 * constant to register" site the way a code patcher would (find a mov
 * whose source operand is an immediate, report its offset and value),
 * cross-checking with AT&T formatting for tools that emit AT&T syntax.
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
    /* A small synthetic function:
     *   55            push ebp
     *   8B EC         mov ebp, esp
     *   83 EC 08      sub esp, 8
     *   B8 01 00 00 00 mov eax, 1        <-- the "patch site"
     *   03 C3         add eax, ebx
     *   90            nop
     *   C3            ret
     */
    unsigned char code[] = {
        0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x08,
        0xB8, 0x01, 0x00, 0x00, 0x00,
        0x03, 0xC3, 0x90, 0xC3,
    };
    const unsigned int total_bytes = sizeof(code);
    const unsigned int patch_offset = 6; /* 1 + 2 + 3 */

    x86_insn_t insn;
    char line[512];
    unsigned int count = 0;
    unsigned int consumed = 0;
    unsigned int found_offset = (unsigned int)-1;
    long found_imm = -1;
    unsigned int last_offset = 0;
    enum x86_insn_type last_type = insn_invalid;

    check("x86_init(opt_none) returns 1", x86_init(opt_none, NULL, NULL) == 1);

    /* Pass 1: linear scan, list every instruction. */
    printf("-- disassembly listing --\n");
    while (consumed < total_bytes) {
        unsigned int sz = x86_disasm(code, total_bytes, 0, consumed, &insn);
        if (sz == 0) {
            printf("scan broke at offset %u\n", consumed);
            break;
        }
        x86_format_insn(&insn, line, sizeof(line), intel_syntax);
        printf("%04X  %-20s %s\n", consumed, "", line);
        count++;

        /* Patcher predicate: mov with immediate source operand. */
        if (insn.type == insn_mov &&
            x86_operand_count(&insn, op_explicit) == 2 &&
            x86_operand_2nd(&insn)->type == op_immediate) {
            found_offset = consumed;
            found_imm = (long)x86_operand_2nd(&insn)->data.dword;
        }
        last_offset = consumed;
        last_type = insn.type;
        x86_oplist_free(&insn);
        consumed += sz;
    }
    printf("--------------------------\n");

    check("scan covered the whole buffer", consumed == total_bytes);
    check("exactly 7 instructions found", count == 7);

    check("patch site found at offset 6", found_offset == patch_offset);
    check("patch site immediate is 1", found_imm == 1);

    check("last instruction is the ret at offset 14",
          last_offset == 14 && last_type == insn_return);

    /* Cross-check the patch site with AT&T syntax (tools emitting AT&T). */
    {
        unsigned int sz = x86_disasm(code, total_bytes, 0, patch_offset, &insn);
        check("re-decode of patch site consumes 5 bytes", sz == 5);
        x86_format_insn(&insn, line, sizeof(line), att_syntax);
        check("att text is 'mov\\t$0x00000001, %eax'",
              strcmp(line, "mov\t$0x00000001, %eax") == 0);
        x86_oplist_free(&insn);
    }

    check("x86_cleanup() returns 1", x86_cleanup() == 1);

    printf("%d/%d assertions passed\n", checks - failures, checks);
    return failures ? 1 : 0;
}
