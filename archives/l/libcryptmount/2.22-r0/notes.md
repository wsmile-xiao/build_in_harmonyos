# libcryptmount 2.22-r0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-20
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化编译环境（init-build）
2. 应用 autotools 补丁（E007/E072）修复 config.guess/config.sub
3. 安装依赖库：
   - linux-pam（PAM headers）从本地 apk 解压包安装
   - libHX 从本地 apk 解压包安装
   - libxml2 2.15.3 从 cmd-pkgs 预编译包安装
   - libxml2-dev 头文件从 Alpine apk 解压安装
   - libmount, libblkid, libuuid 预安装
4. 设置环境变量：
   - PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig
   - CFLAGS=-I/storage/Users/currentUser/usr/local/include
   - LDFLAGS=-L/storage/Users/currentUser/usr/local/lib
   - TMPDIR=/storage/Users/currentUser/tmp（关键：修复 config.status 临时文件问题）
5. Configure: `./configure --prefix=/storage/Users/currentUser/usr/local --without-cryptsetup`
6. 手动修改 config.status 使用 TMPDIR（修复 HMDFS 临时目录限制）
7. Make: `make -j2`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | E007：GNU config.guess 不支持 HarmonyOS | 使用已有补丁修复（build-aux/config.guess.patch） |
| 2 | config.sub 三元组验证失败 | E072：config.sub 不支持 ohos-linux | 使用已有补丁修复（build-aux/config.sub.patch） |
| 3 | 缺少 PAM headers | 项目依赖 linux-pam | 从本地 apk 解压包安装 |
| 4 | 缺少 libHX | 项目依赖 libHX >= 4.28 | 从本地 apk 解压包安装 |
| 5 | 缺少 libxml2 头文件 | 预编译包不含 dev 文件 | 从 Alpine libxml2-dev apk 解压安装 |
| 6 | config.status 无法创建临时文件 | HMDFS/SELinux 权限限制 + mktemp 创建目录权限问题 | **已解决**：修改 config.status 使用 `mkdir -p "$TMPDIR/conf$$"` 而非 `mktemp -d "./confXXXXXX"` |
| 7 | nullptr 未声明 | C 代码使用 C++ nullptr | 替换为 NULL |
| 8 | libmount.h 未找到 | include 路径不匹配 | 修改为 `#include <libmount/libmount.h>` |
| 9 | .la 文件包含错误路径 | 构建机器路径残留 | 手动修复 dependency_libs 和 libdir |

## 源码修改

1. **src/crypto.c** - nullptr → NULL（2处）
2. **src/mtcrypt.c** - nullptr → NULL（2处）
3. **src/rdconf1.c** - nullptr → NULL（4处）
4. **src/mount.c** - `#include <libmount.h>` → `#include <libmount/libmount.h>`
5. **build-aux/config.guess** - 添加 HarmonyOS/__OHOS__ 检测（E007补丁）
6. **build-aux/config.sub** - 添加 ohos-linux 三元组支持（E007补丁）

## 依赖版本

- linux-pam: 1.7.1-r2
- libHX: 4.28-r0
- libxml2: 2.15.3（预编译） + 2.12.10-dev（头文件）
- libmount: 2.20
- libblkid: 预安装
- libuuid: 预安装
- libpcre2-8: 系统版本
- libcrypto: 系统版本

## 补丁列表

| # | 文件 | 类型 | 描述 |
|---|------|------|------|
| 0001 | src/crypto.c | source | nullptr → NULL |
| 0002 | src/mount.c | source | libmount.h → libmount/libmount.h |
| 0003 | src/mtcrypt.c | source | nullptr → NULL |
| 0004 | src/rdconf1.c | source | nullptr → NULL |
| 0005 | build-aux/config.guess | platform | HarmonyOS 平台识别 |
| 0006 | build-aux/config.sub | platform | ohos-linux 三元组支持 |

## 编译产物

- libcryptmount.so.0.0.0（共享库）
- pam_mount.so（PAM 模块）
- mount.crypt, umount.crypt（加密挂载工具）
- pmvarrun（用户会话管理工具）
- autoloop（自动回环设备工具）

## 知识提取

### E-TMPDIR-FIX（新增）
config.status 在 HMDFS 上无法创建临时目录的问题：
- 问题：autoconf 生成的 config.status 使用 `mktemp -d "./confXXXXXX"`，HMDFS 文件系统限制导致创建失败
- 解决：修改 config.status 使用 `mkdir -p "$TMPDIR/conf$$-$RANDOM"` 替代 mktemp
- 适用范围：所有 autotools 项目在 HMDFS 上编译时遇到类似问题
---

**编译结束**: 2026-05-20 22:35
**最终状态**: built
