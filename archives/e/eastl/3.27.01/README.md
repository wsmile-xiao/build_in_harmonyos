# eastl 3.27.01

EASTL 是 Electronic Arts 开发的 C++ 标准模板库实现。

- 上游：https://github.com/electronicarts/EASTL
- 源码：官方 3.27.01 发布版归档，SHA-256 已在 `conandata.yml` 中固定
- 构建：CMake；默认生成静态库
- Conan 依赖：`eabase/0699a15`
- 许可证：BSD-3-Clause

配方会构建并运行上游 EASTL 测试套件。仅供测试使用的 EA 框架依赖从固定版本的官方源码归档获取，不作为供应商源码纳入软件包。软件包会携带已构建的上游测试程序，以便 `test_package` 在目标平台再次运行该程序及消费者检查。可移植性补丁只调整 EAThread 测试框架，使其适配 OHOS libc，并为上游编译器探测报告但 OHOS 不支持的 128 位整数原子读改写操作增加禁用开关；该 API 在 OHOS 软件包中禁用，并通过特性定义告知消费者。消费者检查覆盖定长 vector/string 操作，以及一个需要链接的 EASTL allocator 外部符号。
