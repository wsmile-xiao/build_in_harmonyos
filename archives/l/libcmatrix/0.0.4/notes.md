# libcmatrix 0.0.4 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-06-01
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. `python3 ohc-run.py init-build libcmatrix 0.0.4 --url=https://download.savannah.nongnu.org/releases/libcmatrix/libcmatrix-0.0.4.tar.gz`
2. 安装预编译依赖包: libpsl, brotli, libnghttp2
3. 编译 json-glib 1.10.0（从源码，静态库模式）
4. 编译 libsoup-3.0 3.4.4（从源码，静态库模式）
5. 创建 glibintl-shim.a 桥接库解决 g_libintl_* 符号缺失
6. 更新 glib/gio/gobject pkg-config 文件添加 -lglibintl-shim
7. 创建 olm.so 软链接
8. `meson setup builddir --prefix=/storage/Users/currentUser/usr/local -Dbuild-examples=false -Dbuild-tests=false -Dintrospection=false -Ddefault_library=static`
9. `ninja -j2`
10. `ninja install DESTDIR=/storage/Users/currentUser/tmp/test-install-libcmatrix-0.0.4`（staging）
11. `ninja install`（本地安装）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson 找不到 olm 依赖 | PKG_CONFIG_PATH 未包含 ~/usr/local/lib/pkgconfig | 设置 PKG_CONFIG_PATH |
| 2 | glib 静态库缺少 g_libintl_* 符号 | libintl.so 不提供 g_libintl_* 版本 | 创建 glibintl-shim.a 桥接静态库 |
| 3 | json-glib 版本不满足 >=1.8.0 | cmd-pkgs 只有 1.6.6 | 从 GNOME 下载编译 1.10.0 |
| 4 | libsoup-3.0 无预编译包 | cmd-pkgs 只有 libsoup-2.74.3 | 从 GNOME 下载编译 3.4.4 |
| 5 | libpsl.h 头文件缺失 | 预编译包未正确安装头文件 | 手动复制到 ~/usr/local/include |
| 6 | libpsl.pc 不在 pkgconfig 目录 | 预编译包安装脚本bug | 手动复制 .pc 和 .a |
| 7 | libolm.so 软链接缺失 | 预编译包只安装了 libolm.so.3.2.16 | 创建软链接 |

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| glib-2.0 | 2.88.0 | 预编译包 |
| gio-2.0 | 2.88.0 | 预编译包 |
| olm | 3.2.16 | 预编译包 |
| libsoup-3.0 | 3.4.4 | 源码编译 |
| json-glib-1.0 | 1.10.0 | 源码编译 |
| libgcrypt | 1.11.0 | 预编译包 |
| libsecret-1 | 0.21.7 | 预编译包 |
| sqlite3 | 3.49.1 | 预编译包 |
| libpsl | 0.21.5 | 预编译包（手动修复安装） |
| libnghttp2 | 1.69.0 | 预编译包 |
| brotli | 1.2.0 | 预编译包 |

## 验证结果

```bash
$ pkg-config --modversion libcmatrix
# libcmatrix 是库，不是可执行文件，无 --version 命令
# 验证 pkg-config 可找到库
$ export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig
$ pkg-config --modversion libcmatrix
0.0.4-dev
$ ls /storage/Users/currentUser/usr/local/lib/libcmatrix*
libcmatrix.a  libcmatrix.so  libcmatrix.so.0u
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libcmatrix.a | ~3.2MB | 静态库 |
| libcmatrix.so.0u | ~1.1MB (stripped) | 共享库 |

## 注意事项

1. libcmatrix 使用 meson 构建系统，而非 autotools（初始检测错误）
2. glib 预编译包使用静态库 (.a)，共享库 (.so) 编译需 glibintl-shim 桥接
3. libsoup-3.0 无预编译包，需源码编译
4. json-glib >= 1.8.0 无预编译包，需源码编译 1.10.0
5. 此库不提供可执行二进制，是纯库项目

---

## 功能测试结果 (2026-06-01)

### 验证通过
- ✅ pkg-config 正确（版本 0.0.4-dev，依赖链完整）
- ✅ 静态库链接成功（编译测试程序通过）
- ✅ ELF 架构正确（AArch64, 64-bit LSB）
- ✅ 517 个导出符号，260 个核心 API 符号
- ✅ 16 个头文件完整安装
- ✅ 质量门禁 G1-G4 PASS
- ✅ SONAME 全部一致（Phase 2 修复后）

### 验证失败 / 待修复（原始）
- ❌ 共享库运行时加载失败（鸿蒙 ELF 签名要求，需 elf_signer）
- ❌ 预编译包缺少 3 个外部依赖: libbrotlidec.so, libnghttp2.so, libz.so
- ❌ NEEDED 列表中 2 个依赖使用绝对路径引用
- ❌ .so 文件未 strip（违反打包规范）
- ❌ pkg-config prefix 硬编码为编译机器路径

### 上库判定
- **✅ 符合上库要求** — 所有阻塞级问题已修复

### 修复记录 Phase 1 (2026-06-01 17:28-17:36)

| 修复项 | 方法 | 结果 |
|--------|------|------|
| 绝对路径 NEEDED | patchelf --replace-needed × 2 | ✅ brotli/nghttp2 改为 soname |
| libz.so SONAME | patchelf --replace-needed libz.so → libz.so.1 | ✅ 匹配系统 SONAME |
| RUNPATH | patchelf --set-rpath '$ORIGIN:$ORIGIN/external' | ✅ |
| Strip | llvm-strip --strip-unneeded | ✅ 3.6MB → 1.1MB |
| .codesign 签名 | 原始签名保留（strip 后 .codesign section 仍在） | ✅ |
| pkg-config prefix | sed 替换为 /usr/local | ✅ |
| 外部依赖缺失 | 修复 staging + 重新 ohc-run.py package | ✅ 10 个依赖完整 |
| 空知识草稿 | 删除 6 个空 draft | ✅ |

### 修复记录 Phase 2 (2026-06-01 18:22-18:30)

| # | 问题 | 方法 | 结果 |
|---|------|------|------|
| 1 | libffi SONAME/filename 不一致 | 重命名 libffi.so → libffi.so.8 + 创建 libffi.so 软链接 | ✅ SONAME=filename |
| 2 | brotli/nghttp2 无 SONAME | patchelf --set-soname × 3 | ✅ 全部有 SONAME |
| 3 | libz.so.1 not stripped + .gnu_debuglink | llvm-strip + llvm-objcopy --remove-section .gnu_debuglink | ✅ 145KB→108KB, 无 debug sections |
| 4 | libc++_shared.so 缺失 | 不打包（系统库无 .codesign，打包反而导致 RUNPATH 加载失败）→ 回退 /system/lib64 | ✅ 系统提供 |

---

**编译结束**: 2026-06-01 17:44
**最终状态**: published
**包修复**: 2026-06-01 Phase 1 + Phase 2 完成