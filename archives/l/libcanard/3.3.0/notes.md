# libcanard 3.3.0

## Source

上游仓库：https://github.com/OpenCyphal/libcanard（Cyphal/CAN 传输层 C 实现，MIT 协议）。

版本说明：上游 v3 产品线最新 tag 为 3.2.0（commit 00f9d5ce），截至 2026-09-14
上游尚未发布 3.3.0 tag。本配方按任务版本 3.3.0 建目录，源码取官方
3.2.0 发布包（R39 官方源），SHA256 如下：

```
ff88f86be1bea71f267d8b3bdc20097ab81289edb8458f2b7cfd8b4f8268495c
```

源码包内容（35 个文件）：`libcanard/canard.c`、`libcanard/canard.h`、
`libcanard/_canard_cavl.h`（库本体，仅依赖 C 标准库）、`tests/`（Catch2
单测套件，catch.hpp 为上游 vendored，无需联网获取测试框架）。

## Build

上游没有 install 目标（文档要求直接把 `canard.c`/`canard.h` 拷贝进消费
项目）。配方在 `build()` 中按 linenoise 模式生成最小 `CMakeLists.txt`，
把 `canard.c` 编成 `libcanard` 静态/共享库，头文件安装到
`include/canard/`，消费者以 `#include <canard/canard.h>` 使用。

构建配置：`CMakeToolchain`，`BUILD_SHARED_LIBS` 跟随 `shared` 选项
（默认静态，嵌入式友好）。平台校验仅接受 `Linux`/`OHOS`（R32 口径）。

## Tests

上游测试：`tests/` 下 9 个 `.cpp` 文件共 33 个 `TEST_CASE`（已清点：
private_cavl 10、private_crc 1、private_rx 3、private_tx 5、
public_filters 4、public_roundtrip 1、public_rx 6、public_tx 2、
self 1），由 `tests/CMakeLists.txt` 编成 3 个矩阵
（test_private 19 用例、test_private_crc_table 1 用例、test_public 13 用例），
每个矩阵 4 种变体（x64/x32 × C99/C11），共 12 个 ctest 测试项。

OHOS 适配点（`patches/0001-tests-ohos-aarch64.patch`，POSIX 兼容方式，
未引入任何平台宏，PF5 合规）：

1. 测试矩阵硬编码 x86 专用 `-m32`/`-m64`，aarch64 clang 直接报错；
   补丁在非 x86_64 目标上清空这两个 flags，12 个 ctest 变体仍全部
   原生构建运行（用例数不减少）。
2. 测试可执行文件统一链接 `pthread`；HarmonyOS libc 内含 pthread API，
   无独立 libpthread，补丁在 `CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS"`
   时跳过该链接（测试本身不直接使用线程）。

`build()` 中以 `-DNO_STATIC_ANALYSIS=ON -DNO_CANARD_SANITIZER=ON` 配置上游
测试（clang-tidy 与 sanitizer 运行时在真机上不可用；仅关闭检测工具，
不减少用例），`ctest --output-on-failure` 真实执行，结果解析自
`X% tests passed, Y tests failed out of Z` 汇总行并以
`HMBS_UPSTREAM_TEST_RESULT` 标记输出；同时落盘
`res/upstream_test_result.json` 供 test_package 重发（防缓存命中丢失证据）。

test_package 消费者测试（`test.c`，TAP 16 检查，全部实质调用库 API）：
版本宏、instance 初始化默认值、TX 入队/查看/出队及计数、RX
订阅/查询（3.2 新增 `canardRxGetSubscription`）/退订、过滤器 helper
（`canardMakeFilterForSubject/Service`、`canardConsolidateFilters`）。
`test()` 中 `self.run` 真实执行二进制，再以 subprocess 解析 `ok` 行计数，
输出 `HMBS_TEST_PACKAGE_RESULT` 标记；用例失败时二进制非零退出且
`ok` 行缺失，门禁可捕获（非静默通过）。

## OHOS  notes

- 库本体为纯 C（仅 `#include <string.h>`），无系统调用、无外部依赖，
  无需平台分支。
- 非系统同名库，保留动态库构建能力（默认静态），R26 不适用。
- 纯库项目，无可执行产物，不创建 `commands.json`（R38）。
