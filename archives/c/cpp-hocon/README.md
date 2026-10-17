# cpp-hocon

Puppet Labs 的 HOCON（Human-Optimized Config Object Notation）配置文件
格式 C++ 解析库，TypesafeConfig 的 C++ 移植版。

- 上游: https://github.com/puppetlabs/cpp-hocon
- 许可证: Apache-2.0
- 构建系统: CMake
- 适配版本: 0.3.0（2026-09-09，鸿蒙 PC aarch64）

## OHOS 适配

上游构建体系依赖 puppetlabs/leatherman（CMake 宏框架 + i18n + 工具库，
未发布 OHOS 包）。适配策略：lib/compat 下提供最小 leatherman header
shim（boost::format 实现占位符格式化），CMake 构建脚本重写为纯 CMake
（保留全部源码与上游 unit_tests 测试目标）。详见 0.3.0/notes.md。

## 依赖

- boost1.84/1.84.0（filesystem/program_options/regex 静态库 + headers）
- boost1.84-thread/1.84.0（thread/tss 静态库）
- catch/1.12.2（测试框架，Catch v1）
