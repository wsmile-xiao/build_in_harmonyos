# atools-apkbuild-lint

Alpine Linux `atools` 项目中的 APKBUILD shell 脚本 linter（`apkbuild-lint`）。
对应 Alpine aports `community/atools` 的子包 `atools-apkbuild-lint`，扫描
APKBUILD 打包脚本中的常见错误（默认变量冗余、引号/缩进问题、坏版本号正则、
secfixes 注释格式等），以 `[ALxx]` 标签行输出诊断结果。

## 功能概述

- 纯 POSIX/ash shell 实现（约 630 行），无需编译
- 对每个 APKBUILD 并行运行 30+ 条检查规则，输出 `severity:[ALxx]:file:line:msg`
- 退出码：发现违规为 1，干净为 0；可直接接入 CI 门禁
- 规则标签语义见上游 man 页 alint(5)

## OHOS 适配

- 脚本 shebang `#!/usr/bin/env ash` → `#!/bin/sh`（OHOS 无 ash）
- 上游测试套件（tests/*.bats，bats 框架 224 用例）在真机由配方内置的最小
  BATS 兼容驱动 bats-shim.sh 完整执行；secfixes-check 相关 100 个用例所需的
  lua5.3 解释器由配方从官方 lua-5.3.6 源码现构建（仅测试期使用）
- 本包只安装 `bin/apkbuild-lint`（对齐 Alpine 子包边界）

## 依赖关系

- 无编译依赖、无运行期库依赖（shell + toybox 工具链）

## 参考资料

- 上游仓库：https://gitlab.alpinelinux.org/Leo/atools
- Alpine 包：https://pkgs.alpinelinux.org/package/edge/community/x86_64/atools
- 版本目录：`archives/a/atools-apkbuild-lint/20.2.2/`
