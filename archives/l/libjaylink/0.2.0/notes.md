# libjaylink 0.2.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-04
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 源码获取：从 GitHub syntacore/libjaylink 克隆（zip 包）
2. 运行 autoreconf -i -v 生成 configure 脚本
3. 修改 configure 中的 umask 077 → umask 022（HMDFS 文件系统权限限制）
4. 运行 ./configure --prefix=/storage/Users/currentUser/usr/local
5. 手动修改 config.h 启用 HAVE_LIBUSB（pkg-config 检测失败问题）
6. 手动修改 libjaylink/Makefile 启用 USB 相关源文件和编译选项
7. 运行 make -j1 编译
8. 运行 make install DESTDIR=/storage/Users/currentUser/tmp/test-install-libjaylink-0.2.0
9. 运行 make install 安装到 ~/usr/local

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | autogen.sh 中 aclocal 报错 "am_AUTOM4TE@ inaccessible" | automake 版本兼容性问题 | 使用 autoreconf -i -v 替代 autogen.sh |
| 2 | configure 报错 "can't create ./confRawGtW/subs1.awk: Permission denied" | HMDFS 文件系统的 SELinux 权限限制，umask 077 导致临时文件无法写入 | sed -i 's/umask 077/umask 022/g' configure |
| 3 | configure 输出 USB 支持缺失 "no (missing: libusb-1.0)" | PKG_CONFIG_PATH 环境变量未能正确传递到 configure 内部的 PKG_CHECK_MODULES | 手动修改 config.h 启用 HAVE_LIBUSB，修改 Makefile 启用 USB 相关源文件和编译选项 |
| 4 | 链接报错 "undefined hidden symbol: discovery_usb_scan" | Makefile 中 USB 相关的源文件列表被注释掉（因为 configure 认为 HAVE_LIBUSB=no） | 手动取消 Makefile 中 am__append_1/2/3 和 am__objects_1 的注释 |

## 源码修改

无补丁文件。所有修改都在生成的 configure、config.h 和 Makefile 文件中完成，属于平台适配和构建系统配置问题。

关键修改：
1. configure（第 14755、14760 行）：umask 077 → umask 022
2. config.h：`/* #undef HAVE_LIBUSB */` → `#define HAVE_LIBUSB 1`
3. libjaylink/Makefile：
   - 启用 `am__append_1 = discovery_usb.c transport_usb.c`
   - 启用 `am__append_2 = $(libusb_CFLAGS)`
   - 启用 `am__append_3 = $(libusb_LIBS)`
   - 启用 `am__objects_1 = libjaylink_la-discovery_usb.lo libjaylink_la-transport_usb.lo`

## 依赖版本

- libusb-1.0: 1.0.27（预编译包安装）
- autoconf: 2.72
- automake: 1.17
- libtool: 已安装
- pkg-config: 已安装（>= 0.23）

## 验证结果

```bash
# pkg-config 验证
export PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
pkg-config --modversion libjaylink
# 输出: 0.2.0

pkg-config --cflags --libs libjaylink
# 输出: -I/storage/Users/currentUser/usr/local/include -L/storage/Users/currentUser/usr/local/lib -ljaylink

# 库文件检查
ls -la ~/usr/local/lib/libjaylink*
# 输出:
# libjaylink.a (静态库)
# libjaylink.so.0.0.0 (动态库)
# libjaylink.so.0 -> libjaylink.so.0.0.0
# libjaylink.so -> libjaylink.so.0.0.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libjaylink-0.2.0-ohos-aarch64.tar.gz | 590KB | 预编译包，包含动态库、静态库、头文件和 pkg-config 文件 |

## 注意事项

1. **PKG_CHECK_MODULES 检测问题**：本环境存在 pkg-config 环境变量传递问题，configure 内部的 PKG_CHECK_MODULES 未能正确检测到已安装的 libusb。临时解决方案是手动修改生成的配置文件。更好的方案是在 configure 前设置 `PKG_CONFIG` 环境变量或修改 configure.ac 的检测逻辑。

2. **UMASK 权限限制**：HMDFS 文件系统对临时文件创建有严格权限限制，需要将 configure 中的 umask 077 改为 umask 022。这是一个通用的平台适配问题，建议记录到知识图谱。

3. **无测试套件**：libjaylink 没有提供 make check 测试，无法进行功能性验证。仅能通过 pkg-config 和库文件存在性进行基本验证。

4. **库特性**：这是一个共享库，没有可执行文件，主要用于为其他程序提供 J-Link 设备访问接口。主要使用者是 OpenOCD 等调试工具。

## 知识提取记录

### E{N}: HMDFS umask 限制导致 autotools configure 失败

- **错误模式**: configure 执行时报 `can't create ./confXXXXXX/subs1.awk: Permission denied`
- **根因**: HMDFS 文件系统的 SELinux 权限限制，umask 077 导致临时目录无法写入
- **解决方案**: `sed -i 's/umask 077/umask 022/g' configure`
- **适用范围**: 所有使用 autotools 构建系统的软件
- **建议**: 加入 pre-scan-rules.yaml，在 configure 前自动修复

---
**编译结束**: 2026-06-04
**最终状态**: built（成功编译，预编译包已创建）
---

**编译结束**: 2026-06-04 10:37
**最终状态**: built
