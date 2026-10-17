# date 3.0.5 适配笔记

## 来源核验

- 官方仓库：https://github.com/HowardHinnant/date（Howard Hinnant 的 C++ 日期/时间库）
- 正式 tag：`v3.0.5`（tag commit `179a6b921ccd6179b5b04dce812a89f71a51b4df`，GitHub API 核验）
- 官方 tarball：`https://github.com/HowardHinnant/date/archive/refs/tags/v3.0.5.tar.gz`
- SHA-256（实际下载计算）：`ef786edc203daec76475825640b3af247bd08e31fc52217e5ce8f76107b4bb05`
- tzdata 测试数据：IANA `tzdata2026b`，SHA-256 `114543d9f19a6bfeb5bca43686aea173d38755a3db1f2eec112647ae92c6f544`（实际下载计算）
- 底稿归档：date/3.0.3（本仓库既有条目，作者 junshi_liu）；参考归档 howard-hinnant-date/3.0.4

## 编译环境

- 构建系统：CMake（上游默认 `CMAKE_CXX_STANDARD 17`）
- 编译器：clang/clang++ 15.0.4（Conan OHOS profile 注入，`aarch64-linux-ohos`）
- 平台：HarmonyOS PC aarch64（os=OHOS, arch=armv8, musl）

## 配方策略（沿用 3.0.3 底稿）

配方构建并安装 header-only 的 `date::date` 与静态优先的 `date::date-tz`。时区库使用 `MANUAL_TZ_DB=ON`，由应用通过 `date::set_install()` 指定 tzdata 目录。

| 问题 | 根因 | 解决方案 |
|------|------|----------|
| 默认时区下载模式引入 curl | 上游在非 system/manual 模式下启用远程 tzdata API | 使用 manual tzdb，消除未强验证的隐式依赖 |
| system tzdb 可能假设 `/usr/share/zoneinfo` | OHOS 设备不保证 Linux 的目录布局和软链接行为 | 不启用 `USE_SYSTEM_TZ_DB`，由消费者显式提供 tzdata |
| Conan 包名与上游 CMake 包名不同 | 归档名为 `date`，上游导出 `date`，CMakeDeps 暴露 `date::date` `date::date-tz` | `package_info()` 映射 `cmake_file_name=date`，组件 `date` 与 `date-tz` |
| compile-fail helper 硬编码 `/bin/bash` | Harmony PC 的 bash 位于 `PATH`（`/data/service/hnp/bin/bash`），不存在 `/bin/bash` | 将主脚本及生成 helper 的 shebang 改为 `/usr/bin/env bash`（0001） |
| `current_zone()` 忽略 POSIX `TZ` | Harmony PC 不提供上游探测的 `/etc/localtime` 等系统时区文件 | 仅在 `TZ` 可定位为 IANA zone 时采用；规则串、冒号路径和无效值安全回退到原平台探测链（0002） |
| 测试二进制加载 `libc++_shared.so` 失败 | 设备 shell 的 `LD_LIBRARY_PATH` 含分隔符后空格（`...chipset-pub-sdk: /system/lib64`），带前导空格的路径无效 | 配方 `build()` testit 环境与 `test_package` `test()` 显式 `LD_LIBRARY_PATH=/system/lib64` |

## 与 3.0.3 上游差异（影响补丁的验证结论）

逐文件 diff v3.0.3 与 v3.0.5 官方 tarball，差异文件：CMakeLists.txt、README.md、include/date/{date,islamic,iso_week,julian,ptz,solar_hijri,tz}.h、src/tz.cpp、test/date_test/parse.pass.cpp、test/solar_hijri_test/parse.pass.cpp、test_fail.sh。

- `date.h` 等：`operator "" _d/_y` 改为 `OPERATOR_LITERAL` 宏（老 GCC 兼容）、`%c` 解析 `rs`→`ru` 修复、负年份解析注释修正；islamic/iso_week/julian/solar_hijri 同步 OPERATOR_LITERAL 调整。
- `src/tz.cpp`（19 行差异）：remote tzdb 下载路径、shell 命令引号加固（`rm -R "folder"`）、下载列表空 word `continue`；`current_zone()` 区域无改动。
- `CMakeLists.txt`：`project(date VERSION 3.0.4)`（⚠️ 上游打 v3.0.5 tag 时未同步 bump，tarball 仍为官方 v3.0.5 tag，Conan 版本号维持 3.0.5）、iOS 判断泛化为 APPLE_MOBILE_PLATFORM、CURL 链接改用 `CURL::libcurl` target。
- 测试 TU 清单与 3.0.3 完全一致（108 个 .pass.cpp/.fail.cpp 文件逐一相同，仅内容级修改）。

**补丁适用性验证方式**：对 v3.0.5 源码树执行 `patch -p1 --dry-run` 逐补丁验证：

1. `0001-use-env-bash-for-compile-fail-tests.patch`：**3.0.3 原版 patch 部分过时**——hunk 2（test_fail.sh）FAILED（上游 v3.0.5 已改用 `#!/bin/sh`，天然可移植，无需再打）；hunk 1（compile_fail.sh）仍必要。**按 3.0.5 重新生成为仅含 compile_fail.sh 的补丁**（shebang 三处 `/bin/bash` → `/usr/bin/env bash`），重新生成后 `patch -p1` 干净应用、结果与 3.0.3 语义一致。
2. `0002-honor-tz-environment-for-current-zone.patch`：**仍适用**（tz.cpp `current_zone()` 上下文未变），按 3.0.5 行号重新对齐（`@@ -4200`），同时保留 zoned_time_deduction 回归断言。重新生成时初版把 `testCurrentZoneTzEnvironmentFallback()` 调用误插到模板函数 `testDeductionFrom` 内的 using 声明后（3.0.3 该锚点在 main()，3.0.5 文件头出现了同名 using），导致一次编译失败；修正为锚定 `int main()` 内首条 using 之后，编译通过。zoned_time_deduction.pass.cpp 的 includes hunk 与断言函数 hunk 与 3.0.3 语义相同。

## 源码修改

包含两个最小可移植性补丁：`0001-use-env-bash-for-compile-fail-tests.patch` 让官方 compile-fail 测试从 `PATH` 解析 bash；`0002-honor-tz-environment-for-current-zone.patch` 让非 Windows `current_zone()` 尝试采用可定位的 IANA `TZ`，并对 POSIX 规则串、冒号路径和无效值保留原平台探测链。`0002` 同时为既有 `zoned_time_deduction` CTest 增加 IANA 与 fallback 回归断言（上下文按 3.0.5 源文件重新对齐）。未删减、跳过或豁免任何上游测试 case。

## 依赖版本

无 Conan 三方依赖。`date-tz` 在 OHOS 上链接系统 pthread。

## 测试设计

配方在 package build 中启用官方 `ENABLE_DATE_TESTING` 并执行 `testit`。测试使用固定 IANA `tzdata2026b`（SHA-256 `114543d9...`）、`LC_ALL=C`、`LANG=C`、`TZ=UTC` 和 `LD_LIBRARY_PATH=/system/lib64`（设备环境 LD_LIBRARY_PATH 分隔符后含空格，显式固定以保测试可执行）。上游源码口径 108 个测试翻译单元；本地 `conan create` 实际发现并运行 108 个 CTest case，108/108 通过、0 失败、0 未运行、0 豁免（完整日志：`$HOME/tmp/date-3.0.5-conan-create.log`，"100% tests passed, 0 tests failed out of 108"）。

真实 `test_package.cpp` 沿用 3.0.3（逐一核对仍实质调用被测包 API），链接已打包的 `date::date-tz`，执行 220 个 consumer assertions，覆盖 Gregorian 日期构造与算术、格式化/解析、ISO week、Julian、Islamic、Solar Hijri，以及非内联的 `date::set_install()` 符号（test() 输出 `date checks passed: 220`）。

## 注意事项

- 消费者若使用时区查询 API，必须先准备 tzdata 并调用 `date::set_install()`。
- 包本身不启用运行时远程下载模式；固定 tzdata 只在官方上游测试构建阶段下载并校验（`core.sources:download_cache` 已预填 tarball，规避 GitHub 间歇性超时）。
- 上游 v3.0.5 tarball 的 CMake project 版本仍为 3.0.4（上游未 bump），不影响包内容与测试。
- 不创建 `commands.json`：产物是库和头文件，不是命令行工具。
---

**编译结束**: 2026-09-02 02:28
**最终状态**: built
