# partimage 0.6.9 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-05
- 编译器: clang 15.0.4 / clang++
- 目标平台: aarch64-unknown-linux-ohos (HarmonyOS)
- 状态: published

## 编译步骤

1. 初始化: `ohc-run.py init-build partimage 0.6.9`
2. 替换 config.guess/config.sub 为 automake-1.17 版本（支持 OHOS 目标三元组）
3. 修改 configure.ac: 添加 --disable-newt 和 --disable-ssl 选项
4. 运行 `autoreconf -fi` 重新生成 configure 脚本
5. 修复 configure 和 config.status 中的 `umask 077`（HMDFS 不兼容）
6. 运行 `./configure --prefix=$DEFAULT_PREFIX --disable-newt --disable-ssl`
7. 修复大量编译错误（详见下方问题表）
8. `make -j1` → 编译成功
9. `make install DESTDIR=$TEST_PREFIX` → 安装到 staging 目录
10. 生成补丁: `ohc-run.py refresh-patch --auto partimage 0.6.9` → 45 个补丁文件
11. 验证: `ohc-run.py verify-build partimage 0.6.9`
12. 打包: `ohc-run.py package partimage 0.6.9`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | PRI 宏空格问题 (C++11) | C++11 要求字符串字面量与宏标识符之间有空格: `"%"PRId64` 不合法 | 全局修复所有 `"%"PRIx` → `"%" PRIx`，涉及 fs_base.cpp, imginfo.cpp, misc.cpp, imagefile.cpp 等多个文件 |
| 2 | getspnam/shadow password API 不可用 | HarmonyOS sysroot 有 shadow.h 但无 getspnam 实现 | 在 access.cpp 中用 autoconf 功能检测 `#ifdef HAVE_GETSPNAM` 守卫（configure.ac 补丁在 AC_CHECK_FUNCS 列表追加 getspnam，configure/config.h.in 补丁同步生成检测），无 getspnam 时回退 getpwnam + pw_passwd（AI 检视意见修复，R8 合规：不再使用平台宏 `__OHOS__`） |
| 3 | newt/slang GUI 依赖不可用 | OHOS 预编译仓库无 libnewt/libslang | `--disable-newt` 跳过 newt，在 gui_text.h 中提供 dummy 类替代 |
| 4 | gui_text.h 含 newt 类型 | newtComponent 等类型仅在 HAVE_LIBNEWT 时可用 | 添加 HAVE_LIBNEWT 守卫，无 newt 时提供 CExceptionsGUI, CSavingWindow, CRestoringWindow, CSaveOptWindow, CRestoreOptWindow, CRestoreMbrWindow 等 dummy 类 |
| 5 | CInterface 不完整类型 | 多个文件引用 CInterface 但未包含 interface.h | 添加 `#include "interface.h"` 到 fs_base.h, cbitmap.cpp, imginfo.cpp |
| 6 | gzFile 指针类型不匹配 | OHOS zlib 的 gzFile 是 gzFile_s*（指针），原代码声明 `gzFile *m_gzImageFile`（双重指针） | 改 imagefile.h 中 `gzFile *m_gzImageFile` → `gzFile m_gzImageFile`，移除 gzdopen/gzopen 调用中的 `(gzFile*)` 强制转换 |
| 7 | stray #endif | 之前添加 HAVE_LIBNEWT 守卫时产生多余的 #endif | 修复 main.cpp, fs_jfs.cpp, fs_reiser.cpp, fs_hfs.cpp, fs_xfs.cpp, imagefile.cpp, partimaged-main.cpp 中的 stray #endif |
| 8 | makedev 未定义 | misc.cpp 使用 mknod + makedev，但未包含 sys/sysmacros.h | 添加 `#include <sys/sysmacros.h>` 到 misc.cpp |
| 9 | mode_t 未定义 | common.h 使用 mode_t 但未包含 sys/stat.h | 添加 `#include <sys/stat.h>` 到 common.h |
| 10 | exceptions.h CExceptionsGUI 重复定义 | gui_text.h 和 exceptions.h 都定义 CExceptionsGUI | 重写 exceptions.h 使其包含 gui_text.h，由后者统一处理 |
| 11 | umask 077 与 HMDFS 不兼容 | configure/config.status 中 `umask 077 && mkdir` 创建的目录无法 touch 文件 | 用 sed 移除 configure 和 config.status 中的 `umask 077` |
| 12 | libintl 未链接 | configure 未将 INTLLIBS 加入 LIBS | 在 Makefile.am 中添加 @LIBINTL@ 到 LDADD，并修改生成 Makefile |
| 13 | CPartimagedInterfaceDummy 抽象类 | dummy 类方法签名 char* 与基类 const char* 不匹配 | 修改 partimaged-gui_dummy.h/cpp 中 SetState/SetHostname/SetLocation/SetSize 参数为 const char* |
| 14 | KEY_EXIT/KEY_BACK 未定义 | misc.cpp 使用 newt 键常量 KEY_EXIT/KEY_BACK | 在 gui_text.h dummy 区定义 KEY_OKAY=0, KEY_EXIT=1, KEY_BACK=2 |

## 源码修改分类

### 平台适配类 (功能检测宏守卫)
- access.cpp: getspnam → getpwnam 替代（HAVE_GETSPNAM 功能检测，R8 合规）
- misc.cpp: sys/sysmacros.h 包含

### 条件编译类 (HAVE_LIBNEWT 守卫)
- gui_text.h: 完整重写，提供 dummy 类
- exceptions.h: 重写，包含 gui_text.h
- main.cpp: gui_text.h/interface_newt.h 守卫，interface 初始化条件逻辑
- fs_base.h: 添加 interface.h 和 gui_text.h
- cbitmap.cpp, imginfo.cpp: interface.h 包含
- image_disk.cpp: newtWinMessage 守卫
- partimaged.cpp, partimaged-main.cpp: interface 选择守卫
- 多个 fs_*.cpp: 移除 stray #endif，HAVE_LIBNEWT 守卫

### 类型修复类
- imagefile.h: gzFile* → gzFile
- imagefile.cpp: 移除 (gzFile*) cast

### C++11 兼容类
- 多文件: PRI 宏空格修复

### 构建系统类
- configure.ac: --disable-newt 选项
- Makefile.am (client/server): @LIBINTL@, newt 条件编译
- config.guess/config.sub: 替换为新版本

## configure 参数

```
./configure --prefix=/storage/Users/currentUser/usr/local --disable-newt --disable-ssl
```

关键 config.h 定义:
- HAVE_LIBNEWT: #undef (未定义)
- HAVE_SSL: #undef (未定义)
- HAVE_LIBZ: 1
- HAVE_LIBBZ2: 1
- HAVE_GETTEXT: 1

## 依赖版本

- zlib (OHOS sysroot)
- bzip2 (OHOS sysroot)
- gettext/libintl (~/usr/local/lib)

## 验证结果

```bash
$ file partimage
ELF 64-bit LSB pie executable, ARM aarch64, version 1 (SYSV), dynamically linked, interpreter /lib/ld-musl-aarch64.so.1, with debug_info, not stripped

$ file partimaged
ELF 64-bit LSB pie executable, ARM aarch64, version 1 (SYSV), dynamically linked, interpreter /lib/ld-musl-aarch64.so.1, with debug_info, not stripped
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| partimage (binary) | 535KB | 客户端（分区备份/恢复） |
| partimaged (binary) | 322KB | 服务端 daemon |

## 注意事项

- partimage 在 HarmonyOS 上以 batch/none 模式构建（无 newt GUI），所有交互式对话框使用 dummy 实现
- 若后续 libnewt 可用，可通过 `--enable-newt` 重新编译以启用交互式 GUI
- SSL 支持可通过 `--enable-ssl` 启用（需 libssl/libcrypto）
- shadow password API 不可用，使用普通密码文件替代---

**编译结束**: 2026-06-05 11:39
**最终状态**: built
---

**编译结束**: 2026-08-17 23:29
**最终状态**: published
---

**更新**: 2026-09-17 AI 检视意见修复（PR #4553）
- R8 合规：access.cpp 补丁（0044）移除全部 6 处 `#ifdef __OHOS__` 平台宏，改为 `#ifdef HAVE_GETSPNAM` 功能检测守卫
- 检测链补丁同步更新：0007 (configure.ac) AC_CHECK_FUNCS 列表追加 getspnam；0006 (configure) 插入 ac_fn_c_check_func getspnam 检测；0004 (config.h.in) 添加 `#undef HAVE_GETSPNAM`
- OHOS (musl) 无 getspnam 符号 → 链接测试失败 → HAVE_GETSPNAM 未定义 → 走 getpwnam/pw_passwd 分支，运行时行为与原 `__OHOS__` 版本完全一致
- config.guess 补丁（0003）中的 `#elif defined(__OHOS__)` 为构建系统平台探测的正常模式（检视意见 P3 已认定可忽略），保留
