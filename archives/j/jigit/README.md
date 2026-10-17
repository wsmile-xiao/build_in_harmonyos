# jigit (JTE — Jigdo Template Export)

jigit 是 Steve McIntyre 维护的 JTE（Jigdo Template Export）工具集：用 `libjte` 库高速生成、检视与重建 jigdo 格式的 `.jigdo` + `.template` 镜像描述文件，并附带一组命令行工具（`jigsum`、`jigdump`、`jigit-mkimage`、`parallel-sums` 等）。

## 功能概述
- `libjte`（SONAME `libjte.so.2`，pkg-config 名 `libjte-2`）：模板导出库，多线程计算摘要并写出 `.jigdo`/`.template` 配对文件
- `jte-demo`：上游模板导出 API 的示例驱动（上游为 `noinst` 程序，本包装成可执行，用于端到端往返）
- `jigdump`：检视 `.jigdo`/`.template` 的内容与镜像条目
- `jigit-mkimage`：由 `.jigdo` + `.template` 重建原始镜像
- `jigsum` / `jigsum-sha256`：生成与校验 jigdo 定长 base64 摘要清单（22 字符 MD5 / 43 字符 SHA-256）
- `parallel-sums`：多线程批量摘要
- `extract-data`、`rsyncsum`、`jigdo-gen-checksum-list`（`#!/bin/sh` 脚本）、`mkjigsnap`（Perl 脚本）：镜像子块抽取、rsync 贡献块、十六进制摘要清单、快照辅助

## OHOS 适配
- 构建形态：顶层是手写 Makefile（只有 `all`/`lib` 两个目标，无 configure、无 install），`libjte/` 是其内嵌的 autotools/libtool 子项目；`libjte` 必须 in-source 构建（父 Makefile 直接消费 `libjte_libjte_la-*.o`）。
- E007（configure 认不出 HarmonyOS）：`libjte` 自带 config.guess 2018-02-24 / config.sub 2018-02-22 变体，`scripts/patch-autotools-ohos.pl` 在该变体上实测只打中 1/5，须手工重锚 portability 补丁；不得用 `--build/--host` 绕过（会被误判成交叉编译）。
- E513（musl 无线程取消 API）：`pthread_cancel()` 在链接期即 undefined symbol，改走 `libjte/checksum.c` 既有的 buf/len quit 协议停机，保留 `pthread_exit` + `pthread_join` 回收语义。
- E049（无 FHS 解释器路径）：包内脚本 shebang 硬编码 `/bin/bash`、`/usr/bin/perl`，OHOS 上解释器不存在 ⇒ 直接 ENOENT；`mkjigsnap` 改写为 `#!/usr/bin/env perl` 后走 HNP perl 可启动，上游 `jigit` 包装脚本（`#!/bin/bash` 且写死 apt/wget 流程）不打包。
- `jigdo-gen-checksum-list` 按 `uname -s` 分派且无 HarmonyOS 分支，目标机上直接 `Abort.`，须补分支才能产出 libjte 接受的十六进制摘要清单。
- 已知限制（未修的上游缺陷，与 HarmonyOS 移植无因果关系）：上游同一 tarball 内写出与读取 `[Parts]` 条目的键名形式自相矛盾 ⇒ `[Parts]` 段互通在上游自身即不通；本包未修，口径与证据见 `1.22/notes.md` 的「已知限制」节。
- 3 枚 OHOS portability 补丁（`1.22/conandata.yml` 登记，详见 `1.22/notes.md`）：config.guess/config.sub 重锚、`pthread_cancel` 拆除、`jigdo-gen-checksum-list` 的 HarmonyOS 分支。

## 依赖
- 编译/运行依赖：`zlib/1.3.1`、`bzip2/1.0.8`（顶层 Makefile 无条件 `-lz -lbz2`），`parallel-sums` 另需 `-lpthread`
- 全树无 GTK/GLib/X11 依赖
- 下游接入：`#include <libjte/libjte.h>` + pkg-config `libjte-2`

## 功能验证
- 消费者测试 `1.22/test_package/test_jigit.sh` 全绿：`SUMMARY jigit consumer: total=29 passed=29 failed=0`；分母算法=静态断言站点 20 个，其中 1 个位于 10 元素的 `for` 循环内 ⇒ 20 - 1 + 10 = 29（与 `test_package/MANIFEST.yml` 的 `assertion_count`、`1.22/manifest.yaml` 的 `test_results` 同源）
- 上游无成体系测试（R51 清点：顶层 Makefile 只有 `all`/`lib`，`libjte` 只有 `noinst` 的 test/demo，`add_test` 命中 0），故上述断言全为自建消费者断言
- 端到端往返：`jte-demo` 产出 `.jigdo` + `.template` ⇒ `jigdump` 检视 ⇒ `jigit-mkimage` 重建，产物与母本 `cmp` 全等

## 版本
- 1.22: built（2026-09-27），取源官方址 `https://www.einval.com/~steve/software/JTE/download/jigit-1.22.tar.xz`，sha256 `8a1da3fb7b817174c6c19d71ede19a4b8d0ae433fc5e967d33abf74b545f9954`

## 参考
- 上游主页: https://www.einval.com/~steve/software/JTE/
- 许可证: GPL-2.0-or-later
