# Adaptation Notes - akku 1.1.0

## Overview
Akku.scm 是 Scheme 语言包管理器（CLI 工具），基于 GNU Guile 2.2/3.0。
构建系统：Autotools（configure + make）。

## Build System
- Autotools（configure.ac + Makefile.am），`GUILE_PKG([3.0 2.2])` + `GUILE_PROGS`
- configure 硬性要求 `guild` 二进制与 `guile-2.2.pc`（PKG_CHECK_MODULES）

## 依赖
- guile/2.2.7.1：构建和运行 akku CLI 的 Scheme 解释器与模块环境。
- curl/8.15.0：akku HTTP client 通过 Guile FFI dlopen `libcurl.so.4`，完整 install/update 功能需要运行库可见。
- git：上游 git repository 流程调用 `git` 命令；当前 Conan 归档中 `git/2.49.0` 只有历史 manifest，无可直接消费的 Conan recipe，因此本轮 test_package 只覆盖离线 CLI smoke。

## Build Process
1. 下载 GitLab 官方 sdist `akku-1.1.0.tar.gz`
2. 应用补丁：0001-configure-umask（configure 临时目录 umask 077→022，HMDFS）
3. configure + make -j1
4. make install DESTDIR=package
5. test_package: `akku version` 输出 1.1.0，`akku help` 输出工具说明，并确认 `AKKU` runenv 指向可执行文件。

## OHOS 关键问题与解决
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status: Permission denied | HMDFS umask 077 | 补丁 0001：configure 临时目录 umask 077→022 |
| 2 | guild compile: no such language bytecode | guile 2.2 用 GUILE_LOAD_COMPILED_PATH 查 .go（GUILE_CCACHE_DIR 是 3.0 变量） | akku generate() 注入 GUILE_LOAD_COMPILED_PATH 指向 guile ccache |
| 3 | guild compile: Unbound variable: compile-file / no code for module (ice-9 optargs) | OHOS 上 guile 自动编译失败 | 设 GUILE_AUTO_COMPILE=0，guild 直接使用 ccache 字节码 |
| 4 | guild: //bin/guile: inaccessible | guild 脚本 ${GUILE:-//bin/guile} 回退路径无效（prefix=/） | 显式 env.define("GUILE", guile_bin) |
| 5 | configure: Error loading libguile-2.2.so.1 | configure 运行 guile 时 LD_LIBRARY_PATH 不含 guile lib | 注入 guile 包 lib 到 LD_LIBRARY_PATH |
| 6 | akku --version: Missing required argument | akku CLI 用 version 子命令（srfi-37 args-fold） | test_package 改用 `akku version` |
| 7 | no code for module (industria strings) | akku 自身模块目录未加入 GUILE_LOAD_PATH | package_info() 注入 share/akku/guile/site/2.2 |
| 8 | install/update 运行时可能找不到 libcurl.so.4 | akku HTTP client 运行时 dlopen libcurl | recipe 增加 `curl/8.15.0` 运行时依赖 |
| 9 | configure: `/data/service/hnp/bin/bash: inaccessible or not found` | CI profile 注入的 CONFIG_SHELL/SHELL 在当前真机不可用 | configure 显式走 `/bin/sh`，并在生成环境中覆盖 CONFIG_SHELL/SHELL |
| 10 | configure 找不到 Guile development package | 当前 runner 无 `pkg-config`，而上游 `GUILE_PKG` 必须通过 pkg-config 判定 `guile-2.2` | recipe 生成最小 `pkg-config` wrapper，仅处理 `guile-2.2` 的 exists/cflags/libs 查询 |

## 依赖版本
| 软件 | 版本 | 说明 |
|------|------|------|
| guile | 2.2.7.1 | 构建和运行 akku CLI |
| curl | 8.15.0 | 提供 libcurl.so.4 |

## 验证结果
```bash
$ akku version
1.1.0
$ akku help
Akku.scm 1.1.0 - Scheme package manager
```

上游测试核对：官方发布包 `akku-1.1.0.tar.gz` SHA256 `12decdc8a2caba0f67dfcd57b65e4643037757e86da576408d41a5c487552c08`，包内无 `test/`、`tests/`、`run-tests.sh`、`.gitlab-ci.yml` 或 Automake `TESTS`/`check` 入口；本地上游测试入口数为 0。

真机验证（r6，2026-08-17 06:23:43 +0800 至 06:29:38 +0800）：
- 端口：33332
- run dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-akku-akku-1.1.0-guile-r16-r6-20260817-062343-21438`
- Conan home: `/storage/Users/currentUser/ohos-users/codex-a/guile-2.2.7-cautious-20260816-r2/conan-home`（复用 guile r16 缓存）
- Full package reference: `akku/1.1.0#4647c8b0ac3fb0fb98f0694f3a01179d:e5c123db736e85ad8c6643bcb3c23f663bb00d03#cbd30560eb5607465118586a34801bb2`
- 结果：`RUNNER_RC=0`，Build Summary `Success: 1 / Failed: 0`
- 分层：L0 pass，L1 pass，L2 skip（非阻塞；通用 smoke 使用 `--version/--help`，Akku 正确入口为 `akku version`/`akku help`），L4 pass，L5 pass
- test_package：3/3 断言通过（`akku version`、`akku help`、`AKKU` runenv）
- MemAvailable：8.45GB -> 8.38GB，无 OOM/fork/resource failure

## 交付物
| 文件 | 说明 |
|------|------|
| 0001-configure-umask.patch | configure umask 077→022（HMDFS） |

## 注意事项
1. guile 2.2 字节码路径变量是 GUILE_LOAD_COMPILED_PATH，不是 GUILE_CCACHE_DIR。
2. OHOS 必须 GUILE_AUTO_COMPILE=0（自动编译失败）。
3. akku 版本输出用 `akku version` 子命令。
4. 完整网络安装/更新功能依赖 libcurl 和 git；本轮自动化测试先覆盖离线 CLI 可执行性。
5. 当前 Conan 归档中 `git/2.49.0` 只有历史 manifest，无可消费 recipe，不能作为 Conan `requires()` 引入。
---

**编译结束**: 2026-08-17 06:29:38 +0800
**最终状态**: built
