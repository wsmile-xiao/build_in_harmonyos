# partimage 0.6.9 — HarmonyOS (aarch64) 编译适配

## 基本信息
- **版本**: 0.6.9
- **状态**: published
- **目标平台**: aarch64-unknown-linux-ohos (HarmonyOS)
- **构建系统**: autotools
- **编译器**: clang 15.0.4
- **configure参数**: `--prefix=/usr/local --disable-newt --disable-ssl`
- **补丁数量**: 46

## 补丁说明

本编译需要46个补丁，分为以下类别：

### 1. 构建系统适配 (18个)
- `0001-Makefile.in.patch` ~ `0002-aclocal.m4.patch`: autoreconf重新生成
- `0003-compile.patch`: 添加automake compile辅助脚本（原tarball缺失）
- `0004-config.guess.patch`, `0005-config.sub.patch`: 替换为新版本支持OHOS目标三元组
- `0006-configure.patch`: configure脚本重生成（含umask 077移除）
- `0007-configure.ac.patch`: 添加--disable-newt选项
- `0008-depcomp.patch` ~ `0010-ltmain.sh.patch`: autotools辅助脚本更新
- `0011-m4-Makefile.in.patch` ~ `0016-m4-lt~obsolete.m4.patch`: m4宏文件更新
- `0017-missing.patch` ~ `0018-mkinstalldirs.patch`: 辅助脚本更新

### 2. 源码适配 (28个)
- `0019-src-Makefile.in.patch` ~ `0021-src-client-Makefile.in.patch`: 子目录Makefile重生成
- `0020-src-client-Makefile.am.patch`: 添加@LIBINTL@到LDADD
- `0022-src-client-fs-Makefile.in.patch` ~ `0026-src-client-fs-fs_ufs.cpp.patch`: fs_*文件修复（stray #endif, PRI宏空格等）
- `0027-src-client-gui_text.cpp.patch`: gui_text.cpp修改
- `0028-src-client-image_net.cpp.patch` ~ `0030-src-client-interface_newt.cpp.patch`: 网络和界面相关
- `0029-src-client-imagefile.h.patch`: gzFile* → gzFile类型修复
- `0031-src-client-main.cpp.patch`: HAVE_LIBNEWT条件编译+interface初始化
- `0032-src-client-misc.cpp.patch`: 添加sys/sysmacros.h (makedev宏)
- `0033-src-server-Makefile.am.patch` ~ `0034-src-server-Makefile.in.patch`: 服务端构建文件
- `0035-src-server-partimaged-gui_dummy.cpp.patch` ~ `0037-src-server-partimaged-gui_dummy.h.patch`: dummy界面实现
- `0037-src-server-partimaged-main.cpp.patch`: HAVE_LIBNEWT条件选择Newt/Dummy接口
- `0038-src-server-partimaged.cpp.patch`: 添加partimaged-gui.h + 条件include
- `0039-src-shared-Makefile.in.patch` ~ `0046-src-shared-pathnames.h.patch`: 共享模块适配

## 遇到的主要问题

| # | 问题 | 解决方案 |
|---|------|----------|
| 1 | OHOS无shadow password API (getspnam) | `#ifdef __OHOS__` 守卫，用getpwnam替代 |
| 2 | OHOS zlib gzFile是指针类型（双重指针不兼容） | `gzFile *m_gzImageFile` → `gzFile m_gzImageFile` |
| 3 | C++11要求PRI宏与字符串字面量有空格 | `"%"PRId64` → `"%" PRId64` |
| 4 | newt/slang GUI依赖不可用 | `--disable-newt` + dummy替代类 |
| 5 | umask 077与HMDFS不兼容 | 移除configure/config.status中umask 077 |
| 6 | libintl未链接 | Makefile.am添加@LIBINTL@ |
| 7 | makedev宏需显式include | 添加`#include <sys/sysmacros.h>` |
| 8 | 缺少compile辅助文件 | autoreconf -fi生成并追踪 |

## 依赖
- zlib (OHOS sysroot)
- bzip2 (OHOS sysroot)
- gettext/libintl (用户空间)

## 二进制信息
```
partimage: ELF 64-bit LSB PIE aarch64 executable, dynamically linked
partimaged: ELF 64-bit LSB PIE aarch64 executable, dynamically linked
```

## 注意事项
- 本编译为batch/none模式（无newt GUI），交互式对话框使用dummy实现
- SSL支持未启用（可通过--enable-ssl启用，需libssl/libcrypto）
- shadow password使用普通密码文件替代