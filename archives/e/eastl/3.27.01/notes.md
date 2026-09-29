# EASTL 3.27.01

## 上游与构建

- 上游项目：https://github.com/electronicarts/EASTL
- 版本：官方 `3.27.01` 发布版/标签归档
- 归档：https://github.com/electronicarts/EASTL/archive/refs/tags/3.27.01.tar.gz
- SHA-256：`fce43bf443f5569b00a8deae735394ea0b16f6c3f96867a17ded50775ffcdd12`
- 构建系统：CMake；默认构建静态库
- 运行时软件包依赖：`eabase/0699a15`

源代码发布版的 CMake 项目使用 FetchContent 获取 EABase，上游测试套件还使用另外五个 EA 项目。配方改用经过补丁处理的 Conan EABase 依赖及其生成的 CMake 接口目标，并将另外五个经过校验且固定版本的 EA 源码归档下载到构建源代码树中。此软件包配方不会提交任何上游源码文件。

在 OHOS 上，EASTL 的编译器探测会错误地报告支持 128 位整数原子操作，但此版本并未提供对应的 `fetch_add`/`sub_fetch` API。补丁增加通用禁用宏，OHOS 软件包会传递该定义，从而不向消费者声明此不受支持的 API。另一个补丁只调整 EAThread 测试依赖，使其适配 OHOS libc 支持的接口。上游 `TestAtomicRaw` 测试已修改为：仅当 `compare_exchange_weak` 发生伪失败且期望值保持不变时重试；若确实不匹配，仍会执行原有断言。

## 验证结果

OHOS AArch64 验证：使用 Clang 15 / libc++ 17 以 Release 模式成功完成 `conan create`。Conan 的 `CMake.test()` 会构建 CMake `test` 目标，但不会执行 CTest，因此配方在其后调用 `ctest --test-dir <build>/test --output-on-failure`。上游官方 `EASTLTestRuns` CTest 条目通过 1/1（8.19 s）；直接运行上游测试程序显示 70/70 个具名测试组通过，失败数为 0。测试程序编译了全部 73 个上游 `test/source/*.cpp` 翻译单元。软件包的 `test_package` CTest 通过 2/2（8.04 s）：随包提供的上游测试程序通过 1/1（8.00 s），消费者检查通过 1/1（0.03 s）。消费者检查覆盖定长 vector 插入、对已安装的 EASTL 容器执行 `sort`/`lower_bound`/`find`/`accumulate`、定长 string 追加与比较，以及一个需要链接的 EASTL allocator 外部符号。

OHOS 软件包定义了 `EASTL_DISABLE_ATOMIC_128BIT`，因此不支持的 128 位整数原子读改写 API 不可用，本次验证也未覆盖该 API。堆内存分配覆盖行为未单独测试。
