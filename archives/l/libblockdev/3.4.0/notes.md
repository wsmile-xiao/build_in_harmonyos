# libblockdev 3.4.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-01
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. `./configure --prefix=/storage/Users/currentUser/usr/local --without-btrfs --without-lvm --without-lvm-dbus --without-mpath --without-dm --without-crypto --without-escrow --without-nvdimm --without-nvme --without-smart --without-smartmontools --without-s390 --without-fs --without-part --without-swap --without-tools --without-python3 --without-mdraid --with-loop SHELL=/bin/sh`
2. `make -j1 SHELL=/bin/sh`
3. `make install DESTDIR=/storage/Users/currentUser/tmp/test-install-libblockdev-3.4.0`
4. `make install`（安装到 ~/usr/local）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | HMDFS 不支持 umask 077 | configure 脚本中 `umask 077` 导致安装失败 | 修改 configure， umask 077 → umask 022 |
| 2 | config.guess 不识别 HarmonyOS | 平台三元组缺失 | 在 config.guess 添加 `aarch64-unknown-linux-ohos` 支持 |
| 3 | glib 静态编译链接失败 | glib 编译为 .a，需要 -lintl_glib | Makefile 添加 `-lintl_glib` 链接参数 |
| 4 | libudev/libkmod 无原生实现 | 鸿蒙平台无 udev/kmod 系统库 | 创建 stub 库（返回 NULL/-2），配置时用 stub 的 pkg-config |
| 5 | bd_init 卡住 | kmod stub 初始化时进入循环 | 使用 bd_loop_init() 单独初始化，避免 bd_init 的 kmod 循环 |
| 6 | stub 库 dlopen 失败 | stub 库未 ELF 签名 | 使用 `ohc sign-elf` 对 stub 库签名后可正常加载 |

## 补丁说明（精简为 4 个）

原始 30 个补丁已精简为 4 个合并补丁：

| 补丁 | 内容 | 原编号 | 删除原因 |
|------|------|--------|----------|
| 01-config.guess.patch | 添加 HarmonyOS 三元组识别 | 0001 | — |
| 02-configure.patch | umask 077→022 | 0002 | — |
| 03-m4-libtool-downgrade.patch | m4 宏降级到 libtool 2.4.7 | 0010+0011+0013 合并 | — |
| 04-Makefile.in-automake-downgrade.patch | 全部 Makefile.in 降级到 automake 1.16.5 | 17个合并 | — |

删除的非必需补丁：
- 0006 (spec文件): 可用 configure --without-* 选项替代
- 0012 (ltsugar版权): 仅版权年份变更，无功能影响
- 0014 (lt~obsolete版权): 仅版权年份变更，无功能影响
- 0028 (tests/Makefile): 硬编码 configure 生成文件，不应补丁
- 0024-0026 (python/gi): 已禁用模块，autoreconf 自动处理

## 质量验证结果

- G1 Binary Integrity: PASS
- G2 Functional: PASS (42✅ 3⚠️ 0❌)
- G3 Portability: PASS
- G4 Archive: PASS

## 预编译包

- libblockdev-3.4.0-ohos-aarch64.tar.gz (12.8MB, strip+签名)
- libblockdev-3.4.0-ohos-aarch64-debug.tar.gz (25.8MB, debug symbols)