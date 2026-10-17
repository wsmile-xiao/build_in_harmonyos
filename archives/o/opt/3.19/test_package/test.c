/* test_package/test.c — consumer-side checks for the installed opt static library.
 *
 * 只用 opt.h 的公开 API（optreg_* 注册 + opt()/opt_free() 解析），链接的是 conan
 * 包里已安装的 libopt.a 与 opt.h，不是源码树。
 * 断言逐条用 CHECK 计数：本文件 15 个 CHECK 调用点（不含宏定义行），
 * 与 test_package/MANIFEST.yml 的 assertion_count 一致。
 *
 * optreg_* 的返回值是 0 起的注册槽位序号（opt_reg.c 返回 opt_nreg-1），
 * 因此断言值与下方注册顺序一一对应，改动注册顺序需同步改断言。
 */
#include <stdio.h>
#include <string.h>

#include <opt.h>

static int failures = 0;

#define CHECK(cond, msg)                                   \
    do {                                                   \
        if (cond) {                                        \
            printf("ok - %s\n", (msg));                    \
        } else {                                           \
            printf("FAIL - %s\n", (msg));                  \
            failures++;                                    \
        }                                                  \
    } while (0)

int main(void)
{
    int ival = 0;             /* -a */
    long lval = 0;            /* -l */
    unsigned short usval = 0; /* -n */
    char *sval = NULL;        /* -s */
    int bval = 0;             /* -b */
    double dval = 0.0;        /* -d */
    char *args[] = {"test_opt", "-a", "17", "-l", "123456789",
                    "-n", "-1", "-s", "hello", "-b", "-d", "2.5", NULL};
    int argc = 12;
    char **argv = args;

    /* 1. 安装头里的公开常量自洽 */
    CHECK(OPT_OK == 0, "opt.h OPT_OK == 0");
    CHECK(OPT_MAXSTRLEN == 80, "opt.h OPT_MAXSTRLEN == 80");

    /* 2. 注册 6 个选项：返回 0 起的注册槽位序号 */
    CHECK(optreg_INT(&ival, 'a', "int") == 0, "optreg_INT takes slot 0");
    CHECK(optreg_LONG(&lval, 'l', "long") == 1, "optreg_LONG takes slot 1");
    CHECK(optreg_USHORT(&usval, 'n', "unsigned short") == 2,
          "optreg_USHORT takes slot 2");
    CHECK(optreg_STRING(&sval, 's', "string") == 3,
          "optreg_STRING takes slot 3");
    CHECK(optreg_BOOL(&bval, 'b', "boolean") == 4, "optreg_BOOL takes slot 4");
    CHECK(optreg_DOUBLE(&dval, 'd', "double") == 5, "optreg_DOUBLE takes slot 5");

    /* 3. opt() 一次性解析命令行（已解析项从 argv 消费掉） */
    opt(&argc, &argv);
    CHECK(ival == 17, "opt() parses -a 17 into int");
    CHECK(lval == 123456789L, "opt() parses -l 123456789 into long");
    CHECK(sval != NULL && strcmp(sval, "hello") == 0,
          "opt() parses -s hello into string");
    CHECK(bval == OPT_TRUE, "opt() parses -b into boolean OPT_TRUE");
    CHECK(dval == 2.5, "opt() parses -d 2.5 into double");
    CHECK(argc == 1, "opt() consumed every registered option (argc back to 1)");

    /* 4. 鸿蒙特有（OHOS/aarch64 语义验证）：
     * OPT_USHORT 收到 "-1" 时，opt_atou() 里 (unsigned long)atof("-1") 属 C 未定义行为，
     * aarch64 的 fcvtzu 走饱和语义 → 0；上游 test/checkopt 的对应断言按 32 位回绕期望
     * 65535 / 4294967295，在 64 位 OHOS 上不可能成立（根因与 Debian 同款证据见 notes.md
     * 「上游已知测试缺陷」）。这里把 OHOS 实际语义钉成消费者侧断言，防止将来静默漂移。 */
    CHECK(usval == 0,
          "OHOS/aarch64: OPT_USHORT \"-1\" yields 0 (fcvtzu saturates, not 32-bit wrap)");

    opt_free();

    if (failures) {
        printf("test_opt: %d of 15 assertions FAILED\n", failures);
        return 1;
    }
    printf("test_opt: all 15 assertions passed\n");
    return 0;
}
