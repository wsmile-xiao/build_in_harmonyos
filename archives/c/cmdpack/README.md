# cmdpack

cmdpack 是 Neill Corlett 最初发布的一组二进制与光盘镜像处理命令行工具。
当前维护仓库保留并维护 `bin2ecm`、`uips`、`byteshuf`、`fakecrc` 等 13 个程序。

## 版本列表

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.06 | HarmonyOS CI 已通过（#9022） | 2026-09-08 |

## HarmonyOS 适配说明

- 使用上游原生 Makefile 和 Conan 提供的 C 编译器构建。
- 上游源码仅依赖 libc/POSIX 文件接口，无第三方运行时依赖。
- 上游没有自动化测试套件；`test_package` 会执行全部命令入口，并验证 ECM、IPS、字节重排等核心工作流。
- `ecm2bin` 以 `bin2ecm` 的独立副本打包，避免 HarmonyOS 文件系统上的符号链接兼容问题。
- HarmonyOS CI #9022 已完成 OHOS/armv8 构建和 `test_package` 验证。
