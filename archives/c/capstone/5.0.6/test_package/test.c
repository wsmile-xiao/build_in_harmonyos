/* capstone 5.0.6 —— 真实反汇编验证（非 dlopen 空壳）。
 *
 * 判据：给一段**已知的 aarch64 机器码**，反汇编出的助记符必须对得上。
 *   0xd2800540 = `mov x0, #42`   （MOVZ X0, #0x2a）
 *   0xd65f03c0 = `ret`
 * 这是「换个字节结果就变」的真计算，桩实现蒙不过去；
 * 同时顺带验证 aarch64 架构支持真的编进去了（cs_support）。
 */
#include <capstone/capstone.h>

#include <stdio.h>
#include <string.h>

static int failures = 0;
#define CHECK(c, m) do { if (!(c)) { fprintf(stderr, "[FAIL] %s (%s:%d)\n", (m), __FILE__, __LINE__); ++failures; } \
                         else printf("[ok] %s\n", (m)); } while (0)

int main(void) {
    int major = cs_version(NULL, NULL);
    printf("     capstone 版本号: %d\n", major);
    CHECK(major > 0, "cs_version() 返回正数");
    CHECK(cs_support(CS_ARCH_ARM64), "支持 ARM64/aarch64 架构（本平台必需）");

    csh handle;
    cs_err err = cs_open(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN, &handle);
    CHECK(err == CS_ERR_OK, "cs_open(ARM64) 成功");
    if (err != CS_ERR_OK) { fprintf(stderr, "cs_open: %s\n", cs_strerror(err)); return 1; }

    /* mov x0, #42 ; ret  —— aarch64 小端 */
    const uint8_t code[] = { 0x40, 0x05, 0x80, 0xd2, 0xc0, 0x03, 0x5f, 0xd6 };
    cs_insn *insn = NULL;
    size_t n = cs_disasm(handle, code, sizeof(code), 0x1000, 0, &insn);
    printf("     反汇编出 %zu 条指令\n", n);
    CHECK(n == 2, "反汇编出 2 条指令");
    if (n == 2) {
        printf("       [0] %s %s\n", insn[0].mnemonic, insn[0].op_str);
        printf("       [1] %s %s\n", insn[1].mnemonic, insn[1].op_str);
        CHECK(strcmp(insn[0].mnemonic, "mov") == 0, "第 1 条是 mov");
        CHECK(strstr(insn[0].op_str, "42") != NULL || strstr(insn[0].op_str, "0x2a") != NULL,
              "第 1 条的立即数是 42（0x2a）");
        CHECK(strcmp(insn[1].mnemonic, "ret") == 0, "第 2 条是 ret");
    }
    if (insn) cs_free(insn, n);
    cs_close(&handle);

    if (failures) { fprintf(stderr, "\ncapstone: %d 项断言失败\n", failures); return 1; }
    printf("\ncapstone 5.0.6: 全部断言通过\n");
    return 0;
}
