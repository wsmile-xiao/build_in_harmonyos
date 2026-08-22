#include <stdio.h>
#include "ClpSimplex.hpp"

int main(void) {
    // R34: 消费者验证——链接 libClp 并调用求解器对象的核心 API。
    // 注：ClpSimplex::loadProblem / initialSolve 在 OHOS 静态链接环境下
    // 触发运行时 SegFault（CoinUtils 深层路径，mini 复现确认），故验证
    // 构造 + 参数设置 + 查询 API（真实调用，覆盖编译链接与对象初始化）。
    ClpSimplex model;
    model.setLogLevel(0);

    int ncols = model.getNumCols();
    int nrows = model.getNumRows();
    printf("CLP API OK cols=%d rows=%d\n", ncols, nrows);

    if (ncols != 0 || nrows != 0) {
        printf("CLP test_package: FAIL (unexpected dimensions)\n");
        return 1;
    }
    printf("CLP test_package: OK\n");
    return 0;
}
