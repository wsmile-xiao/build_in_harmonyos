# fff (Fake Function Framework)

fff 是一个单头文件的 C/C++ fake 函数（mock/测试替身）框架：用 `FAKE_VOID_FUNC` /
`FAKE_VALUE_FUNC` 等宏为任意 C 函数生成假实现，自动记录调用计数、实参历史与全局
调用顺序，支持返回值序列与 custom fake 接管，供单元测试中替换真实依赖。

- 上游：https://github.com/meekrosoft/fff
- 许可证：MIT
- 产物：仅 `include/fff.h`（header-only，无库/可执行产物）
- 上游测试：`test/`（C 自制框架 + vendored Google Test）与 `examples/` 三个示例工程
