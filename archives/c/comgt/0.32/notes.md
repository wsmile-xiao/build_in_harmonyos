# comgt 0.32 适配笔记

## 编译环境
- 构建系统: makefile（纯 make，无 configure）
- 编译日期: 2026-09-08
- 编译器: clang 15.0.4（OHOS aarch64）
- 状态: built

## 编译步骤

1. `make -j1`（PATH 前缀垫片 `cc -> clang`）：单文件 comgt.c 编译链接为 comgt。上游 Makefile 规则硬编码 `cc`（非 `$(CC)`），OHOS 主机无 `cc`，故在构建目录生成 `cc` 符号链接并前缀 PATH。
2. 上游测试：上游 0.32（2006 年）无任何自动化测试（tarball 无 test/ 目录，Makefile 无 check/test 目标，可复核 tarball 全清单：comgt.c/comgt.h/comgt.doc/comgt.1/sigmon.1/scripts/Makefile）。
3. Conan 配方：`build()` 显式 PATH 垫片；`package()` 直接拷贝 `comgt` 与 `comgt.1`（上游 install 目标硬编码 /usr/local、/etc/comgt 并 chmod，不可移植）。

## 源码修改（补丁）

| 文件 | 内容 |
|------|------|
| patches/0001-comgt-termios.patch | OHOS musl 无 `<termio.h>`/`struct termio`/`TCGETA`/`TCSETA`：改为 `<termios.h>`/`struct termios`/`TCGETS`/`TCSETS`（字段仅用 c_cflag/c_iflag/c_oflag/c_lflag/c_cc[VMIN|VTIME|VEOF]，逐一核对为 termios 标准成员，映射安全） |

## 上游测试统计

| 口径 | 数值 |
|------|------|
| 上游自动化测试数 | 0（无测试文件、无测试目标，见上证据） |
| 新增消费者测试（test_package/test.sh） | 2 项断言：`comgt -V` 打印版本横幅、`comgt -h` 打印用法指引 |

说明：`comgt -V/-h` 打印后按上游设计经 `ext(1)` 以退出码 1 结束，消费者测试断言 stdout 内容并接受该退出码。

## 源码下载说明

- conandata 使用官方 SourceForge URL（`downloads.sourceforge.net/project/comgt/comgt/0.32/comgt.0.32.tgz`，sha256 与 OpenWrt 记录的上游哈希一致）。
- 设备与 Windows 侧访问 SourceForge 被 Cloudflare 403（镜像主机同样不可达；waterlan.home.xs4all.nl 返回 HTML 非压缩包），本地构建通过 conan 下载缓存预置已核验字节（sha256=0cedb2a5...，与 OpenWrt PKG_HASH、Debian orig tarball 三方一致）解决；CI worker 下载 SourceForge 已有多个合入先例。

## 验证结果

```bash
$ make -j1                       # 构建成功
$ comgt -V                       # comgt version 0.32 ...（exit 1 为上游设计）
$ conan-verify: G0-G4/L2/L4/L5 全部 PASS；test_package 2 断言通过
```

## 已知限制

- 上游将运行脚本安装到硬编码的 `/etc/comgt/`，OHOS 上不可写；包内不安装 scripts/，comgt 内置默认脚本（get_code 内嵌）不受影响，外置脚本需用户经环境/参数自行提供。 modem 硬件相关功能（拨号、PIN）需真实设备，不在消费者测试覆盖范围。
---

**编译结束**: 2026-09-09 02:09
**最终状态**: built
