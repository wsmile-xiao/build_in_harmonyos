# datefudge

datefudge 是一个面向测试场景的轻量级时间模拟工具。它通过私有 `LD_PRELOAD` 共享库
拦截进程读取墙上时钟的调用，无需修改系统时间，也不会影响其他进程。

- 官方仓库：https://salsa.debian.org/debian/datefudge
- 许可证：GPL-2.0-or-later
- 语言：C 与 POSIX shell
- 构建系统：Makefile
- 运行时依赖：coreutils/9.10（GNU `date`）
- 测试依赖：perl/5.42.2

## 功能概述

- 为单个子进程设置动态偏移或静态冻结时间
- 拦截 `time()`、`gettimeofday()` 与 `clock_gettime(CLOCK_REALTIME)`
- 保持文件时间戳和 `CLOCK_MONOTONIC` 不变
- 支持在现有 `LD_PRELOAD` 列表前追加其他库

## HarmonyOS PC 适配

- 使用 OHOS Clang 15 构建 AArch64 musl 共享库
- 启动脚本相对自身位置查找私有共享库，保证 Conan 包可重定位
- 通过 Conan 运行时环境提供 GNU `date`，兼容启动器所需的 `--date` 解析能力
- 使用 Conan Perl 执行官方 `localtime()` 预加载测试
- 在打包阶段完成共享库签名
- 测试覆盖 OHOS/musl 编译宏和 AArch64 ELF ABI

## 依赖关系

构建和运行依赖 HarmonyOS musl libc、动态加载器与系统 shell，并通过 Conan
`coreutils/9.10` 包提供支持 `--date` 语法的 GNU `date`。

## 版本

| 版本 | 状态 | 构建系统 | 验证结果 |
|------|------|----------|----------|
| 1.27 | built | makefile | 上游 9/9、消费者 10/10、HarmonyOS 特有 1/1 |

## 参考资料

- 源码仓库：https://salsa.debian.org/debian/datefudge
- 1.27 标签：https://salsa.debian.org/debian/datefudge/-/tags/debian/1.27
