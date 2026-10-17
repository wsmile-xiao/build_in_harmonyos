# autotools-dev

**GNU config.guess / config.sub 更新基础设施**（Debian 源包，官方维护）

autotools-dev 提供最新版 `config.guess` 与 `config.sub` 脚本，供 automake/libtool 及各类 autotools 构建系统在打包时更新使用。它是 Debian 生态中 `config.{guess,sub}` 文件的权威来源。

## 功能概述

- `config.guess`：根据当前系统运行环境猜测 GNU 系统三元组（triplet）
- `config.sub`：将非标准别名规范化为标准 GNU 系统三元组（含幂等校验）
- 附带上游官方 testsuite（`make check`）：
  - `testsuite/config-guess.data`：153 个 uname 模拟用例
  - `testsuite/config-sub.data`：1161 个 alias→canonical 映射用例 + 幂等/回灌检查

## OHOS 适配

- 纯 shell 脚本包，无 C/C++ 编译步骤；构建阶段即运行上游 testsuite（`make check`）
- `config.sub` 20240727 版已原生支持 OHOS 三元组：`aarch64-linux-ohos -> aarch64-unknown-linux-ohos`
- testsuite Makefile 以裸 `bash` 调脚本，但 HNP bash 在 HMFS/HMDFS 上 getcwd 失败（HMBS 诊断 shell_getcwd）；配方以 `bash -> /bin/sh` 符号链接 shim 前置 PATH 替代，不硬编码 /data/service/hnp/bin/bash
- 交付物为 `share/misc/config.guess` 与 `share/misc/config.sub`

## 依赖关系

- 编译依赖：无（纯脚本）
- 运行依赖：POSIX sh（config.guess/config.sub 均以 `#!/bin/sh` 运行）

## 参考资料

- 上游维护仓库：https://salsa.debian.org/hmh/autotools-dev
- Debian 包页面：https://packages.debian.org/source/sid/autotools-dev
- 源码包：https://deb.debian.org/debian/pool/main/a/autotools-dev/
