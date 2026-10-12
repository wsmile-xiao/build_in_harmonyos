# rsnapshot 1.5.1 鸿蒙PC 适配笔记

## 概况
- rsnapshot 1.5.1 为**纯 Perl 脚本工具**（rsnapshot-program.pl / rsnapshot-diff.pl），autotools 仅做路径探测与替换，无 C 编译。
- 语言预检（R47）判 mixed（perl+bash 主体），但无编译、无 C/C++ 依赖，按脚本工具类包适配（与 archives 中大量 perl-* 包同类），适配成本可控。

## 依赖（W0 全部已在制品仓发布）
- perl/5.42.2 — 运行解释器（buildenv 导出 PATH/PERL）
- rsync/3.3.0 — 快照传输后端
- openssh/10.0p1 — 远程备份

## 构建过程
1. configure 需要 perl/rsync/ssh 在 PATH 上：generate() 中将三个依赖包 bindir 加入 buildenv PATH（R33 合规，源自 Conan 依赖图）。
2. E114 同类问题：HMDFS 上 config.status 的 `mktemp -d ./confXXXXXX` Permission denied。
   方案：`--no-create` 生成 config.status → 将临时目录重定向到 `$TMPDIR/rsnapshot-config-status-tmp` → `bash config.status`（对齐 archives/r/rsync 配方做法）。
3. `make -j1` 生成 rsnapshot / rsnapshot-diff / rsnapshot.conf.default / man 页（pod2man 由依赖 perl 提供）。
4. 安装后 shebang 修正（E049）：configure 将构建时 perl 绝对路径固化进脚本首行 → package() 统一改写为 `#!/usr/bin/env perl`。

## 上游测试（R51 三步法）
- 清点：t/ 目录 17 个测试程序（Test::Harness），`make test` 驱动，共 63 子测试。
- 实测（本机 aarch64 鸿蒙PC，perl v5.42 + conan rsync 3.3.0）：**54/63 通过（85.7%）**。
- 9 个失败子测试全部为同一平台限制：HMFS 不支持硬链接（`link(): Operation not permitted`，E046 同类）。rsnapshot 核心快照机制（cp -al / link_dest）依赖硬链接；本机无任何支持硬链接的可写文件系统（根 tmpfs 无写权限）。CI worker（ext4/tmpfs 可写）或真机本地存储（ext4）上预期全通过。
- test_package 补齐：configtest + 真实 hourly 快照 + 内容校验（单次快照不需要硬链接，全平台可过）。

## 已知限制
- `rsnapshot.conf.default` 中的 cmd_rsync/cmd_ssh 路径为构建时探测值，部署后需按实际路径修改（rsnapshot 设计如此）。
- HMFS 文件系统上无法做多代快照轮转（硬链接限制），属平台限制。
---

**编译结束**: 2026-10-03 08:36
**最终状态**: published
