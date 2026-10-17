/* consumer_use_case.c — libgm2 16.1.1 消费者用例（端到端业务流程）
 *
 * 业务场景：模拟上层业务应用（配置清单预检报告器）。该应用以一段
 * 文本配置清单为输入，调用打包的 Modula-2 运行时 API 完成统计与
 * 校验流程，并输出可观察的报告结果：
 *
 *   C1  用 m2iso_CharClass_IsLetter / IsNumeric / IsUpper 对配置清单
 *       逐字符分类统计（字母数 / 数字数 / 大写数）
 *   C2  用 m2pim_Builtins_strlen 计算清单总长度
 *   C3  用 m2pim_Builtins_strcmp 校验两个配置键的取值是否一致
 *
 * 判定采用手工验算的期望值（见 main 中拆分统计注释），对运行时
 * API 做真实断言，不与被测数据自身对拍。退出码：0=流程全部完成且
 * 结果与期望一致；非 0=业务校验失败。
 *
 * 与 test_package/test_libgm2.c（纯 API 断言）不同：本用例构成一个
 * 完整的"输入 → 处理 → 可观察输出"业务流程，输出供脚本核验。
 */
#include <stdio.h>

/* libm2pim: PIM-style string helpers (C-callable). */
extern unsigned long m2pim_Builtins_strlen(const char *);
extern int m2pim_Builtins_strcmp(const char *, const char *);

/* libm2iso: ISO-style character classification. */
extern int m2iso_CharClass_IsLetter(int);
extern int m2iso_CharClass_IsNumeric(int);
extern int m2iso_CharClass_IsUpper(int);

/* 对一段文本做字符分类统计，返回 0 表示统计完成。 */
static void count_chars(const char *text,
                        unsigned long *letters,
                        unsigned long *digits,
                        unsigned long *upper)
{
    const char *p = text;
    *letters = 0;
    *digits = 0;
    *upper = 0;
    while (*p != '\0') {
        int c = (int)(unsigned char)*p;
        if (m2iso_CharClass_IsLetter(c)) {
            *letters += 1;
            if (m2iso_CharClass_IsUpper(c)) {
                *upper += 1;
            }
        } else if (m2iso_CharClass_IsNumeric(c)) {
            *digits += 1;
        }
        p += 1;
    }
}

int main(void)
{
    /* 配置清单：模拟上层应用的输入数据（含字母、数字、大小写）。
     * 手工拆分统计（ASCII，C locale 语义）——期望值来源：
     *   "CPUCount=8;MemGB=16;Arch=AArch64;" 共 33 字符
     *   letters: CPUCount(8)+MemGB(5)+Arch(4)+AArch64(5) = 22
     *   digits:  8/1/6/6/4 = 5
     *   upper:   CPUCount(4)+MemGB(3)+Arch(1)+AArch64(2) = 10
     */
    const char *inventory = "CPUCount=8;MemGB=16;Arch=AArch64;";
    const unsigned long EXP_LETTERS = 22UL, EXP_DIGITS = 5UL,
                        EXP_UPPER = 10UL, EXP_TOTAL = 33UL;

    unsigned long letters, digits, upper;

    /* C1: 对被测清单做逐字符分类统计。 */
    count_chars(inventory, &letters, &digits, &upper);

    /* C2: 清单总长度。 */
    unsigned long total = m2pim_Builtins_strlen(inventory);

    /* C3: 配置键一致性校验（相等 / 不相等各测一次）。 */
    int same_a = (m2pim_Builtins_strcmp("Arch=AArch64", "Arch=AArch64") == 0);
    int same_b = (m2pim_Builtins_strcmp("Arch=AArch64", "Arch=armv8") == 0);

    /* 业务校验：被测清单的统计必须与手工验算期望值一致。 */
    if (letters != EXP_LETTERS || digits != EXP_DIGITS || upper != EXP_UPPER
        || total != EXP_TOTAL) {
        fprintf(stderr,
                "consumer FAIL: letters=%lu digits=%lu upper=%lu total=%lu"
                " (expected letters=%lu digits=%lu upper=%lu total=%lu)\n",
                letters, digits, upper, total,
                EXP_LETTERS, EXP_DIGITS, EXP_UPPER, EXP_TOTAL);
        return 1;
    }
    if (!same_a || same_b) {
        fprintf(stderr, "consumer FAIL: config key comparison mismatch\n");
        return 2;
    }

    /* 可观察输出：业务流程结果报告（供外部脚本核验）。 */
    printf("letters=%lu digits=%lu upper=%lu total=%lu key_eq=%d key_ne=%d\n",
           letters, digits, upper, total, same_a, !same_b);
    puts("consumer-ok");
    return 0;
}
