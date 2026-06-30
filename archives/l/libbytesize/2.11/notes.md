# libbytesize 2.11 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-01
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 手动下载源码（SSL证书问题，需要 curl -k）并解压到 ~/tmp/builds/
2. 初始化构建上下文：ohc-run.py init-build libbytesize 2.11
3. 打补丁 config.guess/config.sub（E007 + E072）
4. 手动 configure（E011 umask 修复 + 依赖路径设置）
5. 手动 make + make install DESTDIR模式
6. finish built

### 关键 configure 命令
```bash
PKG_CONFIG_PATH=$DEFAULT_PREFIX/lib/pkgconfig \
CPPFLAGS="-I$DEFAULT_PREFIX/include" \
LDFLAGS="-L$DEFAULT_PREFIX/lib" \
./configure --prefix=$DEFAULT_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 HarmonyOS (E007) | 缺少 __OHOS__ 检测分支 | patch-autotools-ohos.pl 补丁 |
| 2 | config.sub 拒绝 aarch64-unknown-linux-ohos (E072) | kernel-os 白名单缺少 linux-ohos* | 手动在 config.sub 第1788行添加 linux-ohos* 和 ohos* |
| 3 | config.status 创建临时目录权限拒绝 (E011) | HMDFS umask 077 导致 UID 映射冲突 | sed -i 's/umask 077/umask 022/g' configure |
| 4 | 缺少 mpfr.h 依赖 | 本地无 mpfr 头文件 | 从 cmd-pkgs 安装 mpfr 4.2.1 预编译包 |
| 5 | 缺少 gmp.h 依赖 | 预编译包安装覆盖丢失 gmp.h | 重新从 gmp 预编译包提取 gmp.h |
| 6 | 链接缺少 libgmp.so/libmpfr.so 共享库 | 预编译包安装覆盖丢失实际库文件 | 从源码编译 GMP 6.3.0（共享库模式）+ 重装 MPFR |
| 7 | install 命令不存在 | HarmonyOS 缺少 GNU install | 使用 ginstall 替代 Makefile.in 中硬编码 install (E080) |
| 8 | curl SSL证书问题 | HarmonyOS 系统证书问题 | 使用 curl -k 或系统 /usr/bin/curl |
| 9 | GMP 静态库缺少 -fPIC | cmd-pkgs 只提供静态库，无共享库 | 从源码编译 GMP 6.3.0 --enable-shared (E083) |
| 10 | bscalc Python shebang 问题 | /usr/bin/python3 不存在 | 修改为 /data/service/hnp/python.org/python_3.12/bin/python3.12 |
| 11 | libbytesize.so 需要 g_libintl_dgettext 符号 | gnulib gettext 重命名规则，符号不在 libintl.so.8 | 需链接 libintl_glib.so (-lintl_glib) |
| 12 | bscalc ctypes dlopen 权限受限 | HarmonyOS 动态链接器拒绝非系统路径库 | 需要 ELF 签名 + 正确 RUNPATH |

## 源码修改

3个补丁文件：
- 0001-config.guess.patch: 添加 HarmonyOS 系统识别 (E007)
- 0002-config.sub.patch: 添加 linux-ohos* 和 ohos* 白名单 (E072)
- 0003-tools-Makefile.in.patch: install→ginstall 替代 (E080, R6)

**非补丁修复**（运行时 sed 修复，不作为补丁上传）：
- umask 077→022: `sed -i 's/umask 077/umask 022/g' configure` (E011)
- CPPFLAGS/LDFLAGS: 通过 env_vars 设置（不需要补丁 configure）

**已删除的冗余补丁**：
- 0001-Makefile.in.patch: 仅是 config.rpath 行的差异（自动生成），不影响编译
- 0004-configure.patch: 8905 行 autoconf 版本升级差异，真正修改仅 2 行 umask，改为 sed 运行时修复
- 0005-dist-libbytesize.spec.patch: spec 文件修改不影响编译
- 0006-tools-Makefile.patch: configure 生成文件，不应作为补丁 (R6)

## 依赖版本

- GMP 6.3.0 (从源码编译，共享库模式)
- MPFR 4.2.1 (预编译包安装)
- PCRE2 10.40 (系统自带)
- gettext 0.22.5 (预编译包，msgmerge等工具)
- automake 1.16.5 (预编译包)
- libtool 2.4.7 (预编译包)

## 功能测试结果

### C API 测试（10/10 PASS）

编译命令：
```bash
clang -Wl,--allow-shlib-undefined -Wl,-rpath,$PREFIX/lib \
  -o test_bs test_bytesize.c \
  -I$PREFIX/include -L$PREFIX/lib \
  -lbytesize -lintl_glib -lintl -lgmp -lmpfr -lpcre2-8
```

> ⚠️ 关键：必须链接 `-lintl_glib`！libbytesize.so 需要 `g_libintl_dgettext` 符号（来自 libintl_glib.so，不是标准 libintl.so.8）

| 测试 | 描述 | 结果 | 详情 |
|------|------|------|------|
| 1 | 创建 Size (1 GiB) | ✅ | bs_size_new_from_str |
| 2 | 创建 Size (512 MiB) | ✅ | bs_size_new_from_str |
| 3 | 创建 Size (0) | ✅ | get_bytes_str = "0" |
| 4 | 加法 1 GiB + 512 MiB | ✅ | = 1.5 GiB |
| 5 | 减法 1 GiB - 512 MiB | ✅ | = 512 MiB |
| 6 | 乘法 512 MiB * 2 | ✅ | = 1024 MiB |
| 7 | 比较 1 GiB > 512 MiB | ✅ | cmp = 1 |
| 8 | 获取字节数 1 GiB | ✅ | = 1073741824 |
| 9 | 从字节数创建 | ✅ | 1073741824 = 1024 MiB |
| 10 | 单位转换 1 GiB→MB | ✅ | = 1073.741824 MB |

### bscalc 工具（受限 ⚠️）

bscalc 是 Python 脚本（#!/usr/bin/python3），在 HarmonyOS 上受限：

| 问题 | 根因 | 解决方案 |
|------|------|----------|
| shebang `/usr/bin/python3` | 路径不存在 | 改为 `/data/service/hnp/python.org/python_3.12/bin/python3.12` |
| ctypes dlopen 权限 | HarmonyOS 动态链接器拒绝非系统路径库 | 需 ELF 签名 + 正确 RUNPATH |
| PYTHONPATH | bytesize 模块不在 Python3.12 sys.path | 设置 PYTHONPATH 或安装到 Python site-packages |

> **可用的运行方式**: `PYTHONPATH=$PREFIX/lib/python3.12/site-packages LD_PRELOAD=$PREFIX/lib/libintl_glib.so /data/service/hnp/bin/python -c "import bytesize; ..."`

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libbytesize.so.1.0.0 | 39296 | 共享库（C API ✅） |
| bscalc | 5278 | 命令行工具（⚠️ Python 脚本受限） |
| bs_size.h | 4105 | 头文件 |
| bytesize.pc | 334 | pkg-config 文件 |

## 注意事项

- E011 (umask 077) 是所有 autotools 项目在 HMDFS 上的常见问题
- E007/E072 是所有 autotools 项目在 HarmonyOS 上的通用补丁
- tools/Makefile.in 中硬编码 `install` 需改为 `ginstall`（R6 铁律：修改源文件）
- GMP 需从源码编译共享库版本，cmd-pkgs 只提供静态库
- **运行 libbytesize.so 的程序必须链接 `-lintl_glib`**（提供 g_libintl_dgettext 符号）
- bscalc 在 HarmonyOS 上受限，C API 是推荐使用方式---

**编译结束**: 2026-06-01 19:14
**最终状态**: built
---

**编译结束**: 2026-06-01 22:44
**最终状态**: built
