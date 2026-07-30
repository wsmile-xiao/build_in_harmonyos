# howard-hinnant-date 3.0.4 适配笔记

## 编译环境

- 构建系统：CMake
- 编译日期：2026-07-22
- 编译器：clang/clang++（由 Conan OHOS profile 注入）
- 状态：built（设备验证结果以 Builder 报告为准）

## 配方策略

配方构建并安装 header-only 的 `date::date` 与静态优先的 `date::date-tz`。时区库使用 `MANUAL_TZ_DB=ON`，由应用通过 `date::set_install()` 指定 tzdata 目录。

| 问题 | 根因 | 解决方案 |
|------|------|----------|
| 默认时区下载模式引入 curl | 上游在非 system/manual 模式下启用远程 tzdata API | 使用 manual tzdb，消除未强验证的隐式依赖 |
| system tzdb 可能假设 `/usr/share/zoneinfo` | OHOS 设备不保证 Linux 的目录布局和软链接行为 | 不启用 `USE_SYSTEM_TZ_DB`，由消费者显式提供 tzdata |
| Conan 包名与上游 CMake 包名不同 | 比赛归档名为 `howard-hinnant-date`，上游导出 `date` | `package_info()` 映射为 `date::date` 和 `date::date-tz` |
| compile-fail helper 硬编码 `/bin/bash` | Harmony PC 的 bash 位于 `PATH`，不存在 `/bin/bash` | 将主脚本及生成 helper 的 shebang 改为 `/usr/bin/env bash` |
| `current_zone()` 忽略 POSIX `TZ` | Harmony PC 不提供上游探测的 `/etc/localtime` 等系统时区文件 | 仅在 `TZ` 可定位为 IANA zone 时采用；规则串、冒号路径和无效值安全回退到原平台探测链 |

## 源码修改

包含两个最小可移植性补丁：`0001-use-env-bash-for-compile-fail-tests.patch` 让官方 compile-fail 测试从 `PATH` 解析 bash；`0002-honor-tz-environment-for-current-zone.patch` 让非 Windows `current_zone()` 尝试采用可定位的 IANA `TZ`，并对 POSIX 规则串、冒号路径和无效值保留原平台探测链。`0002` 同时为既有 `zoned_time_deduction` CTest 增加 IANA 与 fallback 回归断言。未删减、跳过或豁免任何上游测试 case。

## 依赖版本

无 Conan 三方依赖。`date-tz` 在 OHOS 上链接系统 pthread。

## 测试设计

配方在 package build 中启用官方 `ENABLE_DATE_TESTING` 并执行 `testit`。测试使用固定 IANA `tzdata2026b`（SHA-256 `114543d9f19a6bfeb5bca43686aea173d38755a3db1f2eec112647ae92c6f544`）、`LC_ALL=C`、`LANG=C` 和 `TZ=UTC`。Round 9 上游源码口径为 109 个测试翻译单元；设备运行时实际发现 108 个 CTest case，结果为 108/108 通过、0 失败、0 未运行、0 豁免，原始证据为 `howard-hinnant-date_device_round9.log`。

真实 `test_package.cpp` 另行链接已打包的 `date::date-tz`，执行 220 个 consumer assertions，覆盖 Gregorian 日期构造与算术、格式化/解析、ISO week、Julian、Islamic、Solar Hijri，以及非内联的 `date::set_install()` 符号。220 是断言数，不是 CTest case 数。

## 注意事项

- 消费者若使用时区查询 API，必须先准备 tzdata 并调用 `date::set_install()`。
- 包本身不启用运行时远程下载模式；固定 tzdata 只在官方上游测试构建阶段下载并校验。
- 不创建 `commands.json`：产物是库和头文件，不是命令行工具。
