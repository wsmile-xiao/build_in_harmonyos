# nfcutils 0.3.2 — 适配笔记

## 概述

| 项 | 值 |
|---|---|
| 上游 | https://github.com/nfc-tools/nfcutils（0.3.2，2013-06） |
| 形态 | 纯 C、autotools；单工具 lsnfc（src/lsnfc.c，约 500 行） |
| 依赖 | libnfc >= 1.7.0（pkg-config）→ 仓内 1.8.0；静态链需显式 -lusb -lusb-1.0 |
| 许可证 | GPL-3.0-or-later |
| 源 | google-code-archive（storage.googleapis.com，仓内 4 例同域名先例实证 CI 可达） |
| sha256 | dea258774bd08c8b7ff65e9bed2a449b24ed8736326b1bb83610248e697c7f1b（Homebrew == 本地） |

## 补丁清单

| 补丁 | 类型 | 说明 |
|---|---|---|
| 0001-config.guess.patch | portability | config.guess（2012 版）主 case 增加 `*:HarmonyOS:*:*` 分支 → 输出 `aarch64-unknown-linux-ohos`（E007 模式，参考 libnfc 0001） |
| 0002-config.sub.patch | portability | config.sub 增加 `linux-ohos*`（maybe_os 列表，122 行）与 `-linux-ohos*`（os 有效性列表，1353 行）两处（E007） |
| 0003-configure.patch | platform | configure 6108-6114 行 `umask 077` → `022`（mktemp/mkdir 临时目录，HMDFS 077 目录拒写） |

## 关键决策

1. **链接依赖注入**：libnfc 1.8.0 为静态库，`libnfc.pc` 的 `Requires:` 为空
   （libnfc configure.ac `PKG_CONFIG_REQUIRES=""`），pkg-config 展开只给 `-lnfc`。
   libnfc.a 内部引用 libusb-compat（usb_*）与 libusb-1.0（libusb_*）符号 →
   配方 generate() 遍历传递依赖收集 `-l` 注入 LIBS（依赖者在前），
   LD_LIBRARY_PATH 注入依赖 libdir（conftest 运行需要）。与 libnfc 配方同手法。
2. **pkg-config 消费**：configure 的 `PKG_CHECK_MODULES([libnfc],[libnfc>=1.7.0])`
   标准检测；PKG_CONFIG_PATH 注入 libnfc.pc 所在目录即命中，无需覆盖变量。
3. **测试断言以上游真实行为为准**：任务预估"无硬件非零退出"，但源码实证
   lsnfc 无设备时打印 `ERROR: No device found.` 后 `return EXIT_SUCCESS`（0）——
   test_package 断言退出码 0 + 输出含 `No device found`（如实）。
4. **上游无测试**：归档 20 文件、唯一源码 lsnfc.c、Makefile.am 仅 bin_PROGRAMS，
   无 tests/ 无 check target。test_package 消费者冒烟 3 断言接入（R34）。

## 踩坑记录

- `.opendesk-tmp` 目录被系统清理（含已下载 tarball 与解压树）→ 研究工作区迁移到
  `~/Hawkninja/work/nfcutils-research/`（tarball 保留副本，sha256 兜底可随时重下）。
- 手写补丁 hunk 行号偏差导致 0002 patch 应用失败（hunk 头 -123 实际 -122）→
  改为「干净副本修改 + diff -u 生成补丁」方式，全部补丁在 patch-test 副本 dry-run 验证通过。
- libnfc 1.8.0 上游 tarball 的 libnfc.pc.in 确认存在（configure 生成 pc 文件），
  消费方无需 vendor pc。

## 验证状态

- [x] 补丁应用：0001/0002/0003 在干净副本 dry-run 全部 OK
- [ ] conan create EXIT=0（阶段三进行中）
- [ ] test_package 通过（阶段四）
