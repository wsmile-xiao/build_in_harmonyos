// test_pigeonhole.c — 消费者视角验证 libdovecot-sieve 静态库可用性
//
// 验证内容：
//   1. libdovecot-sieve 可链接（隐式验证 libdovecot.a 依赖链完整）
//   2. Sieve 核心公共头 sieve-common.h 可包含（-DHAVE_CONFIG_H + 安装头路径）
//   3. sieve_engine / sieve 相关符号可解析（链接期验证）
// 断言口径见 ../MANIFEST.yml。
#include <sieve/sieve-common.h>
#include <sieve/sieve.h>

#include <stdio.h>
#include <string.h>

#define CHECK(cond) do { \
    if (!(cond)) { \
        fprintf(stderr, "FAIL: %s (line %d)\n", #cond, __LINE__); \
        return 1; \
    } \
} while (0)

/* sieve.h 暴露的符号：sieve_import / sieve_export 等需要完整 dovecot 环境；
 * 这里仅做链接期符号解析 + 头文件可包含性 + 常量存在性校验（不实际运行
 * Sieve 引擎——那需要 dovecot 运行时环境，属沙箱限制范围）。 */
int main(void)
{
    /* 1. sieve.h 核心类型可声明（sieve_script / sieve_error_handler 等） */
    struct sieve_script *script = NULL;
    (void)script;
    struct sieve_binary *bin = NULL;
    (void)bin;

    /* 2. sieve-common.h 的扩展注册 API 符号存在（链接期）——
     *    用 sieve-common.h 中真实定义的核心宏 SIEVE_MAX_NUMBER（上游
     *    SIEVE_VERSION_MAJOR 未定义在公共头，CI #59648 报 undeclared） */
    CHECK(SIEVE_MAX_NUMBER > 0);

    /* 3. 真实引用 libdovecot-sieve.a 库内符号 sieve_close（sieve.h 公共 API，
     *    定义于 src/lib-sieve/sieve.c）——取函数地址并保留为 volatile 变量，
     *    强制链接器按需抽取该符号所在对象（否则静态库零引用时链接器不拉取
     *    .a 内容，"可链接"断言落空）；仅解析地址不调用，避免沙箱运行时依赖 */
    volatile void (*sieve_close_fn)(struct sieve_binary **) = sieve_close;
    CHECK(sieve_close_fn != NULL);

    printf("test_pigeonhole: OK (sieve headers included, lib linked)\n");
    return 0;
}
