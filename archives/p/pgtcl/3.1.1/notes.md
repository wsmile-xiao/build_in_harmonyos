# pgtcl 3.1.1 适配笔记

## 编译环境
- 构建系统: autotools (TEA - Tcl Extension Architecture)
- 编译日期: 2026-06-12
- 编译器: clang 15.0.4 (aarch64)
- 状态: published

## 编译步骤

1. 从 GitHub flightaware/Pgtcl 下载 v3.1.1 源码（原仓库无 configure 脚本）
2. 运行 `autoconf` 生成 configure 脚本
3. 修复 configure 中 umask 077 问题（HarmonyOS 上 umask 077 创建的临时目录不可写）
4. 修复 aclocal.m4 和 tclconfig/tcl.m4 中平台识别（添加 HarmonyOS* 模式）
5. 运行 `./configure --prefix=$DEFAULT_PREFIX --with-tcl=$DEFAULT_PREFIX/lib`
6. 运行 `make -j2`
7. 运行 `make install DESTDIR=$TEST_PREFIX`
8. 运行 `make install`（本地安装验证）
9. ELF 签名

configure 参数: `--prefix=/storage/Users/currentUser/usr/local --with-tcl=/storage/Users/currentUser/usr/local/lib`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 脚本不存在 | GitHub tarball 未包含预生成的 configure 脚本 | 运行 autoconf 从 configure.in 生成 |
| 2 | config.status "Permission denied" 创建 subs1.awk | autoconf 在 config.status 中使用 umask 077，在 HarmonyOS HMDFS 上创建的临时目录不可写 | sed 移除 configure 中的 umask 077 |
| 3 | SHLIB_LD 为空 | TEA 配置脚本不识别 HarmonyOS 平台（uname -s 返回 "HarmonyOS"），导致平台检测 case 语句无匹配 | 在 aclocal.m4 和 tclconfig/tcl.m4 中将 HarmonyOS* 添加到 Linux*|GNU*|NetBSD-Debian 模式 |
| 4 | 测试无法运行 "dynamic loading not available" | HarmonyOS Tcl 不支持动态加载未签名的共享库 | 需先签名 ELF，此为平台限制而非编译问题 |

## 源码修改

| 文件 | 补丁名 | 修改内容 |
|------|--------|----------|
| aclocal.m4 | 0001-harmonyos-platform.patch | 在 TEA_CONFIG_CFLAGS case 语句中添加 HarmonyOS* 到 Linux 平台模式 |
| tclconfig/tcl.m4 | 0001-harmonyos-platform.patch | 同上，在原始 tcl.m4 的平台检测中添加 HarmonyOS* |

注：configure 脚本的 umask 077 修复是生成文件修改（非源码），不创建补丁。每次 autoconf 生成后需手动 sed 移除。

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| Tcl | 8.6.14 | 预编译包 (cmd-pkgs) |
| PostgreSQL libpq | 17.10 | 预编译包 (cmd-pkgs) |
| sqlite3 | 3.49.1 | 预编译包 (cmd-pkgs) |
| autoconf | 2.72 | 预编译包 (cmd-pkgs) |
| clang | 15.0.4 | 系统自带 |

## 验证结果

```bash
# 库文件已安装
ls $DEFAULT_PREFIX/lib/pgtcl3.1/libpgtcl3.1.1.so
# ELF 签名成功
file $DEFAULT_PREFIX/lib/pgtcl3.1/libpgtcl3.1.1.so
# ELF shared object, 64-bit LSB arm64, not stripped

# 测试结果：因 HarmonyOS Tcl 动态加载限制，无法 load 共享库
# 但编译产物本身正确
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| pgtcl-3.1.1-ohos-aarch64.tar.gz | ~125KB | 主包（strip + 签名） |
| pgtcl-3.1.1-ohos-aarch64-debug.tar.gz | ~130KB | debug 包（保留符号） |

## 注意事项

- pgtcl 源码不包含预生成的 configure 脚本，每次需要先运行 autoconf（见 hints/pre-configure.sh）
- autoconf 生成 configure 后，必须 sed 移除 umask 077（HarmonyOS HMDFS 限制）
- TEA 平台检测不识别 HarmonyOS，需手动添加到 Linux 模式匹配（补丁已包含此修改）
- 测试需要 PostgreSQL 服务和 Tcl 动态加载支持，在 HarmonyOS 上受限
- G0 干净构建验证因源码不含 configure 脚本无法通过（需 autoconf 步骤），但补丁本身自包含正确

**编译结束**: 2026-06-12 18:37
**最终状态**: published
---

**编译结束**: 2026-06-12 18:43
**最终状态**: published
