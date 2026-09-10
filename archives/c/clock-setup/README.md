# clock-setup 0.168 for HarmonyOS

## 概述

clock-setup 是 Debian installer（debian-installer）的时钟配置 udeb。本次适配的
可移植编译产物是其中的单文件 C 工具 `set-date-epoch`：当系统日期早于
1970-01-01 时将其回拨到 epoch；时钟正常时静默退出 0。

| 项目 | 值 |
|------|-----|
| 名称 | clock-setup |
| 版本 | 0.168 |
| 上游仓库 | https://salsa.debian.org/installer-team/clock-setup |
| 源码包 | https://deb.debian.org/debian/pool/main/c/clock-setup/clock-setup_0.168.tar.xz |
| 许可证 | GPL-2.0 |
| 构建系统 | 裸 Makefile（`make -j1 build`，CC 由 Conan 注入） |
| 产物 | bin/set-date-epoch |

## 鸿蒙适配要点

- 沿用上游 Makefile，不修改源码、无补丁；`CC` 从 Conan conf
  `tools.build:compiler_executables` 获取（R33），`make -j1`（R9）。
- 动态链接：二进制仅依赖系统 libc，无外部 Conan 依赖（不触发 R36 链式发布），
  产物名唯一，无 R26 系统同名污染风险。
- 上游 debconf shell 脚本（postinst/finish-install hook）依赖 debian-installer
  环境，不参与构建与测试。

## 上游测试

上游无测试套件（no_tests）：源码树无 tests/ 目录；Makefile 无 check/test 目标；
debian/rules 仅对 2 个 shell 脚本做 `sh -n` 打包期语法检查（0 用例）。显式审计见
`0.168/test_package/MANIFEST.yml`。test_package 提供 6 项内容级功能用例真实执行
bin/set-date-epoch：存在且可执行、两处程序字符串检查、正常时钟退出码 0、
stdout 为空、stderr 为空。

## 验证

在 HarmonyOS aarch64 环境实测（以 CI 最终结果为准）：

```bash
# 随包测试由 conan create 自动执行（6 项内容级用例）
# 手工复核：set-date-epoch 在正常时钟下静默退出 0
set-date-epoch; echo $?
# 预期输出：0（无任何输出）
```

## 参考资料

- https://salsa.debian.org/installer-team/clock-setup
- https://tracker.debian.org/pkg/clock-setup
