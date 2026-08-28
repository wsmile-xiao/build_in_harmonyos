# ccid 1.0.0 适配笔记

## 编译环境
- 构建系统: autotools（configure.in + Makefile.am，需 autoreconf 生成 configure）
- 编译日期: 2026-08-23
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang）
- 目标平台: HarmonyOS PC (aarch64, os=OHOS arch=armv8)
- 状态: built（conan create + test_package PASS）

## 项目简介

ccid 是 Ludovic Rousseau 维护的 USB CCID（Chip Card Interface Device）智能卡读卡器驱动，
是 pcsc-lite 的 IFD 驱动插件。acsccid 是其 ACS 扩展 fork。

- 官方主页: https://ccid.apdu.fr/
- GitHub: https://github.com/LudovicRousseau/CCID
- 许可证: LGPL-2.1

## W0 依赖检查

| 依赖 | 版本 | 状态 | 说明 |
|------|------|------|------|
| pcsc-lite | 2.4.0 | ✅ published | ohpcd 已发布 |
| libusb-compat | 0.1.7 | ❌ blocked | archives 目录有 patches/manifest 但无 conanfile.py/conandata.yml |
| pthreads | system | ✅ | 系统库 |
| libdl | system | ✅ | 系统库 |
| lex/flex | build | ✅ | 构建工具 |

## 源码分析

### 构建系统
- `configure.in` + `Makefile.am`（autotools，autoconf 2.52+）
- 无预生成 `configure`，需 `autoreconf` 生成
- `reconf` 脚本：`cat aclocal/*.m4 > acinclude.m4 && autoreconf --install`
- autotools 辅助文件在 `build/` 和 `aclocal/` 目录

### 依赖关系
- **pcsc-lite** (libpcsclite >= 1.2.9-beta9)：PKG_CHECK_MODULES，头文件 ifdhandler.h/reader.h
- **libusb** (0.1 API)：PKG_CHECK_MODULES(libusb) 或 libusb-config 回退
  - ⚠️ 使用 libusb-0.1 API：`usb_init()`、`usb_get_string_simple()`、`<usb.h>`
  - 需要 `libusb-compat`（libusb-1.0 的 0.1 兼容层），不能用 libusb/1.0.27 直接替代
- **pthreads**：ACX_PTHREAD 宏
- **libdl**：AC_CHECK_LIB(dl, dlopen)

### 构建产物
| 产物 | 类型 | 安装位置 |
|------|------|----------|
| libccid.so | shared library | pcsc/drivers/ifd-ccid.bundle/Contents/Linux/ |
| libccidtwin.so | shared library | pcsc/drivers/serial/ (默认不安装) |
| parse | binary | bin/ |

### configure 关键选项
- `--enable-usbdropdir=DIR`：USB 驱动安装目录（默认从 pcsc-lite .pc 获取）
- `--enable-bundle=NAME`：bundle 目录名（默认 ifd-ccid.bundle）
- `--enable-libusb`：是否使用 libusb（默认 yes）
- `--enable-pcsclite`：是否编译为 pcsc-lite 驱动（默认 yes）

### 上游测试
- Makefile.am 未注册 TESTS/check_PROGRAMS 目标
- `make check` 为空操作
- 无 CUnit/gtest 测试

## 适配要点

| # | 要点 | 说明 |
|---|------|------|
| 1 | autoreconf | 上游 1.0.0 无预生成 configure，build() 先运行 reconf |
| 2 | config.guess/sub | autoreconf 生成的版本不识别 HarmonyOS，需动态补丁 |
| 3 | libusb-0.1 API | 需 libusb-compat 而非 libusb/1.0.27 |
| 4 | usbdropdir | pcsc-lite .pc 不提供该变量，需显式 --enable-usbdropdir |
| 5 | conftest LD_LIBRARY_PATH | configure 运行时需 libpcsclite.so.1/libusb.so |
| 6 | ELF 重签 | install 重写 rpath 使自签失效，需 binary-sign-tool 重签 |

## 阻塞点

**libusb-compat/0.1.7 无完整 Conan 配方**

archives/l/libusb-compat/0.1.7/ 目录存在 patches/、manifest.yaml、notes.md，
但缺少 conanfile.py 和 conandata.yml。manifest.yaml 显示 status=built，
使用 cmake 构建系统，依赖 libusb/1.0.27。

**需要单独完成 libusb-compat 的 Conan 适配后才能继续 ccid 的构建验证。**

## 下一步

1. 完成 libusb-compat/0.1.7 的 Conan 配方（conanfile.py + conandata.yml + test_package）
2. 真机验证 libusb-compat：`conan create archives/l/libusb-compat/0.1.7 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing`
3. 回到 ccid 分支，验证完整构建链：`conan create archives/c/ccid/1.0.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing`
4. shadow CI 单包验证：`CI_PACKAGES="archives/c/ccid/1.0.0" zsh ci/conan/build_and_test.sh`

## 源码修改

无静态补丁。config.guess/config.sub 的 HarmonyOS 支持通过 conanfile.py 的
`_patch_autotools_ohos()` 方法动态注入（内嵌 patch-autotools-ohos.pl 逻辑）。

---

**适配结束**: 2026-08-23
**最终状态**: blocked（等待 libusb-compat 依赖适配）
