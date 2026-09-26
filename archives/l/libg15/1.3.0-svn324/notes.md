# libg15 1.3.0-svn324 适配笔记

## 编译环境
- 构建系统: autotools（源码仅含 configure.in + bootstrap，无预生成 configure）
- 编译日期: 2026-09-21
- 编译器: clang 15（/data/service/hnp/bin/clang，OHOS SDK）
- 目标平台: OHOS aarch64（config.guess → aarch64-unknown-linux-ohos，native 构建）
- 状态: published

## 源码来源（R39）
- salsa.debian.org/debian/libg15 仓库 tag `debian/1.3.0_svn324-2`（即 1.3.0~svn324 orig 源码）。
- 归档 URL（官方托管，PF7 官方托管例外）：
  `https://salsa.debian.org/debian/libg15/-/archive/debian/1.3.0_svn324-2/libg15-1.3.0_svn324-2.tar.gz`
- sha256: `5cfd4489b29ce9c90c42acbc76a0323fb567943aeb7fedfc68a2f1743fc76606`
- 该 tar 内含 debian/ 与 rpm/ 打包目录，配方 source() 中仅保留上游部分（删除 debian/、rpm/）。

## 编译步骤

### 探索性编译（Step 2，验证源码可编译）
```bash
# work 树打 Debian 补丁（libusb-0.1 → libusb-1.0）
patch -p1 < debian/patches/01-fix-spelling.patch
patch -p1 < debian/patches/02-switch-to-libusb-1.0.patch

mkdir config
AUTOM4TE=/storage/Users/currentUser/usr/local/bin/autom4te ./bootstrap   # 生成 configure
CC=clang ./configure --prefix=$DEFAULT_PREFIX \
    CPPFLAGS="-I/storage/Users/currentUser/usr/local/include" \
    LDFLAGS="-L/storage/Users/currentUser/usr/local/lib"
make -j1
make install DESTDIR=$TEST_PREFIX
```
- 本地 smoke：`clang -o g15_smoke g15_smoke.c -I$T/include -L$T/lib -lg15`，
  `initLibG15() = 1 (G15_ERROR_OPENING_USB_DEVICE)`，无硬件时返回预期错误码。

### Conan 配方编译（conan create，W3）
- `source()`: 下载 salsa 归档 → `apply_conandata_patches`（Debian 补丁 01/02）→
  删除 debian/、rpm/ → 运行 `./bootstrap` 生成 configure → 改写 configure 中
  `umask 077` → `umask 022`。
- `generate()`: AutotoolsToolchain + libusb 依赖注入：
  `-I<libusb>/include`（CFLAGS + CPPFLAGS）、`-L<libusb>/lib`（LDFLAGS）。
- `build()`: `./configure && make -j1`（out-of-tree，Autotools helper）。
- `package()`: `make install DESTDIR=<pkg>` + 拷贝 COPYING + OHOS 下对
  lib/ 下 .so 做 ELF 代码签名（binary-sign-tool，libaec/libusb 同款）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.status: can't create ./conf*/subs1.awk: Permission denied` | HMDFS 共享目录 umask 077 创建的 0700 临时目录（setgid 继承→2700），构建进程 uid≠目录属主 → 不可写（E112，libusb 同款） | 生成 configure 后 `replace_in_file` 把 `umask 077` 改写为 `umask 022`，临时目录保持组可写 |
| 2 | `aclocal: @am_AUTOM4TE@: inaccessible or not found` | 设备侧 automake 安装未替换模板变量，aclocal 回退到字面 `@am_AUTOM4TE@` | bootstrap 时显式 `AUTOM4TE=$(which autom4te)` |
| 3 | 上游源码使用 libusb-0.1 API（`usb.h`/`usb_*`），无法链接 libusb-1.0 | 上游 2011 年后未更新 | 应用 Debian 官方补丁 `02-switch-to-libusb-1.0.patch`（configure.in + libg15.c 全量迁移），补丁无平台宏（R8/PF5 合规） |

## 源码修改

补丁（源自 Debian debian/patches/ 01+02 官方补丁，refresh-patch 按文件拆分重命名）：
- `patches/0001-configure.in.patch` — configure.in：libusb-0.1 → libusb-1.0（AC_CHECK_LIB usb-1.0、头文件 libusb-1.0/libusb.h）
- `patches/0002-libg15.c.patch` — libg15.c：libusb-1.0 API 全量迁移 + 拼写修正

配方内非补丁修改：
- configure 生成后 umask 077→022（HMDFS 平台工作区兼容，libusb 配方同款，非平台宏）
- bootstrap 前导出 AUTOM4TE

## 依赖版本
- libusb/1.0.27（制品仓 ohpcd 已发布，R36 依赖已就绪）

## R51 上游测试清点（三步法第一步，附证据）
清点方式：解压源码后检索测试声明，实际执行 `make check`。
- **目录清点**：上游树无 tests/、test/ 目录（仅 libg15.c、libg15.h、Makefile.am、configure.in、bootstrap、AUTHORS/COPYING/ChangeLog/INSTALL/NEWS/README、debian/、rpm/）。
- **构建声明清点**：`Makefile.am` 未定义 `TESTS`、`check_PROGRAMS`、`check-local`；`grep -n 'TESTS\|check_PROGRAMS' Makefile.am` 无命中；automake 生成的 `check-am: all-am` 为空 no-op。
- **实测**：`make check` 执行成功但零测试运行（无输出、无测试进程）。执行证据：`make check` rc=0，日志为空。
- 结论：**上游无测试套件**。故 conanfile build() 不执行 make check（避免假阳性 L1c），验证职责全部落在 test_package（R34：实质调 libg15 API）。
- 顺带发现：libg15.c `g15NumberOfConnectedDevices()` 内部循环用 `g15_devices[i]` 而非 `g15_devices[j]`（Debian 打包的上游 bug），无硬件时该路径不触发，不影响编译/链接；无硬件运行场景不会执行到此函数内层。

## 验证结果
```bash
# conan create（本地 W3 实证）
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# test_package 输出：
#   OK: LIBG15_VERSION = 1201
#   OK: initLibG15() = G15_ERROR_OPENING_USB_DEVICE (no G15 hardware; libusb init + device probe executed)
```
上游测试 0/0/通过率 N/A（无测试）；test_package 断言 2/2 通过。

## 交付物
| 文件 | 说明 |
|------|------|
| include/libg15.h | 公共头文件 |
| lib/libg15.so.1.0.1 (+ .so/.so.1 symlink) | 动态库（OHOS 已签名） |
| lib/libg15.a | 静态库 |

## 注意事项
- 本包为外设库（罗技 G11/G15 键盘），无硬件时 `initLibG15()` 返回 `G15_ERROR_OPENING_USB_DEVICE` 属预期行为；setLCDContrast/setLEDs/getPressedKeys 等设备操作在无硬件时不可调用（内部以 NULL keyboard_device 传给 libusb，会崩溃），test_package 因此只覆盖 link + 初始化返回码 + 纯查询 API（R34 无硬件口径）。
- 版本号 `1.3.0-svn324` 对应上游 `1.3.0~svn324`（Debian 版本写法），归档目录/branch 用 `-` 归一化。
- `#include <libusb-1.0/libusb.h>` 需要 `-I<libusb>/include`（而非 libusb cpp_info.includedirs 的 `include/libusb-1.0`），已在配方 generate() 显式注入；configure.in 的 AC_CHECK_HEADERS 只用 `$CPP $CPPFLAGS`，故 -I 同时进 CPPFLAGS。
---

**编译结束**: 2026-09-21 16:20
**最终状态**: published
