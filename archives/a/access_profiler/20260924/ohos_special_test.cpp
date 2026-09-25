// HarmonyOS 专项测试：access_profiler aarch64 适配验证
//
// 验证在 OHOS aarch64 平台上：
//   1. 库自动初始化可用：所有外部链接全局对象（pagemutex/typemutex/pagemap/
//      typemap/access/last_page）在本适配中改为 static 内部链接，本测试验证
//      该适配后库能以 instrument_type 完成真实负载并正常退出（exit 0）；
//   2. aarch64 单步（mcontext.pstate SS 位）故障页记录路径可用：对带
//      instrument_type 的堆对象重复读写，字段访问热区被记录并写盘。
//
// access_profile.out 由库的静态析构（~static_init_t -> print_report）在
// main 返回之后写出，因此"报告内容校验"由运行方（shell）在进程退出后
// 对产物执行：本二进制只保证负载执行与正常退出。
#include <stdio.h>

#include "access_profiler.hpp"

// 复刻上游 test.cpp 的布局（char array[50]; int a; int b），与上游
// README release 输出（test / 52: 1）对齐，便于外部校验。
struct test : access_profiler::instrument_type<test>
{
    test() : a(0), b(0) {}
    char array[50];
    int a;
    int b;
};

int main()
{
    // 真实负载：重复字段读写触发保护页故障与单步记录
    test* t1 = new test;
    for (int i = 0; i < 10; ++i) {
        ++t1->a;
        t1->b += t1->a;
    }
    volatile int sink = t1->b; // 防止整体优化删除
    if (sink < 0) return 2;
    delete t1;

    printf("SPECIAL-TEST-WORKLOAD-OK: instrumented load ran on OHOS\n");
    return 0;
}
