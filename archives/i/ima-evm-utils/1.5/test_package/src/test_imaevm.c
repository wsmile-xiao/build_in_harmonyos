/* ima-evm-utils 消费者用例：真实调用 libimaevm 公开 API + evmctl 工具运行. */
#include <stdio.h>
#include <stdlib.h>

/* imaevm.h 为 libimaevm 公共头（src/imaevm.h 安装到 include/） */
#include "imaevm.h"

int main(void)
{
    int rc = 0;

    /* 断言 1：imaevm_get_hash_algo("sha256") 返回非负哈希算法 ID
     *（libimaevm 真实符号 + libcrypto 依赖链） */
    int algo = imaevm_get_hash_algo("sha256");
    if (algo < 0) {
        fprintf(stderr, "FAIL: imaevm_get_hash_algo(sha256)=%d\n", algo);
        rc = 1;
    } else {
        printf("OK: hash_algo(sha256)->id=%d\n", algo);
    }

    /* 断言 2：imaevm_hash_algo_by_id(id) 返回非空算法名（真实 roundtrip） */
    const char *name = imaevm_hash_algo_by_id(algo);
    if (name == NULL || name[0] == '\0') {
        fprintf(stderr, "FAIL: imaevm_hash_algo_by_id(%d) empty\n", algo);
        rc = 1;
    } else {
        printf("OK: hash_algo_by_id(%d)->%s\n", algo, name);
    }

    /* 断言 3：evmctl 工具可运行（bin_PROGRAMS 公开命令行接口）
     * 路径经 EVMCTL 环境变量注入（conanrun 不保证包 bin 在 PATH） */
    const char *evmctl = getenv("EVMCTL");
    if (evmctl == NULL || evmctl[0] == '\0')
        evmctl = "evmctl";
    char cmd[512];
    snprintf(cmd, sizeof(cmd), "%s --version >/dev/null 2>&1", evmctl);
    int er = system(cmd);
    if (er != 0) {
        fprintf(stderr, "FAIL: evmctl --version exit=%d\n", er);
        rc = 1;
    } else {
        printf("OK: evmctl --version\n");
    }

    return rc;
}
