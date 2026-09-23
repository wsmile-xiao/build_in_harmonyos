/* test.cc — gadap 2.0 消费者测试 (R34: 实质调用被测包 API)。

消费者视角验证:
  1. 链接: 用被测包 (libgadap.a) + libdap 静态库真实链接
  2. API 调用: gadap_numopen / gadap_open (不可达 URL → libdap
     Connect::request_dds 抛 Error → gadap 捕获返回错误码, 完整
     C++ 异常跨库边界传播验证) / gadap_handle 越界错误处理 /
     gadap_sq_new 无效句柄
  3. 断言: 期望行为不符返回非 0

不依赖外部服务器可达性: gadap_open 用 127.0.0.1:1 (本机无监听端口,
连接立即被拒), curl 抛 "Failed to connect" Error。

注意: 不能用本地文件路径测 gadap_open — libdap 3.20.6 的 Connect 对
非 http 名字走 _local 分支 (d_http=0), request_dds 解引用空指针会
segfault (上游设计: gadap/libdap 只支持 OPeNDAP 远程数据源)。
*/
#include <cstdio>
#include <cstring>
#include <string>

#include "gadap.h"

static int failures = 0;

#define CHECK(cond, msg)                                        \
    do {                                                        \
        if (!(cond)) {                                          \
            std::fprintf(stderr, "FAIL: %s\n", msg);            \
            failures++;                                         \
        } else {                                                \
            std::printf("PASS: %s\n", msg);                     \
        }                                                       \
    } while (0)

int main(void) {
    /* 1) 无数据集打开时 gadap_numopen() 必须为 0 */
    int n = gadap_numopen();
    CHECK(n == 0, "gadap_numopen() == 0 with no open datasets");

    /* 2) gadap_open() 不可达 URL → errval(GADAP_ERR_DAP_ERROR) (libdap
     *    Error 异常跨库边界传播, gaConnect 构造中途失败被 gadap 捕获;
     *    上游约定错误码 = -1 * GADAP_ERR_* 枚举值, 见 gadap_err.h) */
    GADAP_DATASET d = -1;
    GADAP_STATUS st = gadap_open("http://127.0.0.1:1/invalid/station.dds", &d);
    CHECK(st != GADAP_SUCCESS, "gadap_open(unreachable URL) fails");
    CHECK(st == -GADAP_ERR_DAP_ERROR, "gadap_open error code is -GADAP_ERR_DAP_ERROR");
    CHECK(d == -1, "dataset handle stays -1 on failure");

    /* 3) 打开失败后 numopen 仍为 0 (未泄漏 dataset 句柄) */
    n = gadap_numopen();
    CHECK(n == 0, "gadap_numopen() == 0 after failed open");

    /* 4) gadap_handle() 越界索引 → 错误码 */
    GADAP_DATASET h2 = -1;
    GADAP_STATUS st2 = gadap_handle(&h2, 0);
    CHECK(st2 != GADAP_SUCCESS, "gadap_handle(out-of-range) fails");

    /* 5) gadap_sq_new() 对无效 handle → NULL (资源分配错误路径) */
    GADAP_STN_QUERY *q = gadap_sq_new((GADAP_DATASET)0);
    CHECK(q == nullptr, "gadap_sq_new(invalid handle) returns NULL");

    if (failures == 0) {
        std::printf("GADAP_TEST_PASS\n");
        return 0;
    }
    std::printf("GADAP_TEST_FAIL (%d failures)\n", failures);
    return 1;
}
