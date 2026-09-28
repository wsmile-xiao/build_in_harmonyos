# trompeloeil-cpp

Header-only C++ mocking framework（上游项目名 trompeloeil，作者 rollbear）。
本包名沿用 Debian 的 `trompeloeil-cpp` 命名，内容与上游 tag `v49` 完全一致：
声明式期望（`REQUIRE_CALL`/`ALLOW_CALL`/`FORBID_CALL`）、参数匹配器、基数与
序列约束、副作用/返回值注入、期望违反报告，以及 C++20 协程 mock。

## 功能概述
- 以宏接口为 mock 对象定义接口与期望，编译期与运行期双重校验
- 匹配器：`_`、`gt`/`lt`、`re`、`any`、成员判断等
- 基数 `TIMES`/`ANY_TIMES`、序列 `IN_SEQUENCE`、`NEVER`/`FORBID_CALL`
- `LR_SIDE_EFFECT`/`RETURN`/`THROW` 注入行为
- C++20 协程：`CO_RETURN`/`CO_YIELD`/`CO_THROW`

## OHOS 适配
- 纯头文件包，无编译产物；`package_id` 清空，对任意配置只有一个二进制包。
- CMake 目标：包内导出 `trompeloeil::trompeloeil`（与上游 CMake 包名一致），
  消费端通过 `find_package(trompeloeil CONFIG REQUIRED)` 使用。
- 上游自带 Catch2 自测与 68 个负向编译用例，配方在 `build()` 中真实编译并运行
  （见版本级 notes.md），不做“头文件存在即通过”式验证。
- 已知平台细节：上游测试 CMake 在 OHOS 上会提示 `System is unknown to cmake`
  （CMake 无 OHOS platform 模块），属良性；HMDFS 上 jobserver `mkfifo` 受限会产生
  非致命警告。

## 依赖关系
- 运行期依赖：无（header-only）。
- 测试期依赖：`catch2/3.8.1`（tool_requires，仅用于编译/运行上游自测与消费者测试）。

## 参考资料
- 上游仓库：<https://github.com/rollbear/trompeloeil>
- 许可证：Boost Software License 1.0（`LICENSE_1_0.txt`）
