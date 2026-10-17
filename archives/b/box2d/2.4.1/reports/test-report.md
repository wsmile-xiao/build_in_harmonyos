# box2d 2.4.1 验证报告

验证日期：2026-09-05

## 验证范围

本报告覆盖 Windows host 本机验证与 HarmonyOS PC aarch64 真机单包 CI。

## Windows host 环境

- Conan 2.31.2
- Visual Studio 2022 / MSVC 194
- CMake 3.31.6
- Windows x86_64，Release，静态库

## Windows host 结果

| 项目 | 结果 |
|------|------|
| 官方源码 SHA256 | 通过：`d6b4650ff897ee1ead27cf77a5933ea197cbeef6705638dd181adc2e816b23c2` |
| Conan `create --build=missing` | 通过，打包 40 个头文件、`box2d.lib` 和 3 个 CMake 配置文件 |
| 上游 `unit_test` | 通过：5/5 test cases，36/36 assertions |
| `test_package` | 通过：6 项消费者断言，真实创建 World/Body 并运行 60 步仿真 |

## Windows host 命令

```powershell
conan create archives/b/box2d/2.4.1 --build=missing
```

说明：GitHub 源码首次下载与 SHA 校验已通过；后续一次 GitHub 超时期间，使用同 SHA256 的本地源码包经临时本机 HTTP 地址完成复验，验证后 `conandata.yml` 已恢复官方 GitHub URL。

## HarmonyOS PC aarch64 真机

- 运行目录：`/storage/Users/currentUser/ohos-test-runs/codex-box2d-2.4.1-r1-20260905-211013`
- commit：`0ceb709439df5d29a1eae9925e9c8dc134c7ebdd`
- 环境：Conan 2.29.1、Clang 15.0.4、`ohos-aarch64`、OHOS 6.0、armv8、Release、静态库
- 并发与内存：`tools.build:jobs=1`、`CMAKE_BUILD_PARALLEL_LEVEL=1`、`MAKEFLAGS=-j1`；构建期间 `MemAvailable` 保持约 14 GB
- 产物：`libbox2d.a` 345232 字节、40 个头文件、3 个 CMake 配置文件；`readelf` 显示 ELF64 AArch64 relocatable

| CI 项目 | 结果 |
|------|------|
| Build Summary | 通过：`Total: 1 / Success: 1 / Pass rate: 100.0%` |
| L0 | pass：质量门禁通过 |
| L1 | pass：上游 `unit_test` 与 `test_package` 均真实执行 |
| L2 | skip：纯库包无 `bin/` 可执行文件 |
| L4 | pass：无补丁 |
| L5 | pass：`lib/libbox2d.a` 存在 |

上游 `unit_test`：5/5 test cases、36/36 assertions 通过。`test_package`：链接并运行 `test_box2d`，输出 `box2d consumer test passed`。

## 真机命令

```sh
CI_PACKAGES="archives/b/box2d/2.4.1" zsh ci/conan/build_and_test.sh
```

执行时设置隔离 `CONAN_HOME`、`TMPDIR`、`TMPPREFIX`，并保持单 job。远端运行日志位于上述运行目录的 `logs/build.log`。

## 第二台真机复验（2026-09-07）

验证日期：2026-09-07 23:33 - 2026-09-08 00:12（Asia/Shanghai）

- 设备：`10.62.134.118:2222`，HarmonyOS PC（HongMeng Kernel 1.12.0 aarch64）
- commit：`691fb3638c`（rebase 后 HEAD，box2d 目录内容与首次验证逐字节一致）
- 源码包：`git archive HEAD` 327178240 字节，MD5 `0ff92e14e68ea82b4bb3a70248fd3919` 双向一致
- 环境：Conan 2.29.1、`ohos-aarch64`、clang++ 15、armv8、Release、静态库
- 并发与内存：`tools.build:jobs=1`、`CMAKE_BUILD_PARALLEL_LEVEL=1`、`MAKEFLAGS=-j1`；全程 `MemAvailable` 16.7-17.6 GB

| CI 项目 | 结果 |
|------|------|
| Build Summary | 通过：`Total: 1 / Success: 1 / Pass rate: 100.0%` |
| L0 | pass：质量门禁通过 |
| L1 | pass：上游 `unit_test` 与 `test_package` 真实执行；L1e 破坏性负向测试确认测试真实依赖包产物 |
| L2 | skip：纯库包无 `bin/` 可执行文件 |
| L4 | pass：无补丁 |
| L5 | pass：`lib/` 有内容 |

`ci-metadata.json` 正常生成（`runner: manual`；设备无 git，`commit: unknown`）。

设备侧适配调整（仅设备运行副本，不改仓库与提交）：`/tmp` 只读需 `TMPDIR` + zsh `TMPPREFIX` 重定向；设备无 `bash`，副本中 `knowledge_check.sh`/`junk_check.sh` 以 `/bin/sh` 运行（POSIX 兼容）；`ci/`、`config/` 文本文件 CRLF 转 LF。
