# opensmtpd-table-socketmap 1.1.1-r0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-17
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 源码 tarball 不含生成的 autotools 文件（无 configure/Makefile.in），需先运行 `autoreconf -vfi`（bootstrap 脚本）
2. VPATH 构建：在独立 build 目录运行 configure，避免 HMDFS 0700 目录权限问题
3. `CC=clang ./configure --prefix=$DEFAULT_PREFIX`
4. `make -j1`
5. `make install DESTDIR=$TEST_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | automake 缺失 | HarmonyOS 未预装 automake | 通过 cmd-pkgs 安装 automake 1.16.5 |
| 2 | aclocal 找不到 Automake/Config.pm | cmd-pkgs automake 二进制为 1.17，但模块在 1.16 目录 | 创建 symlink: automake-1.17/Automake -> automake-1.16/Automake |
| 3 | autoconf 不在 PATH | automake 调用 autoconf 时找不到 | 创建 symlink 到 /storage/Users/currentUser/usr/local/bin/ |
| 4 | config.status 创建临时目录失败 | HMDFS 不允许在 0700 权限目录内创建文件 | 修改 config.status 中 umask 077 为 umask 022 |

## 源码修改

无补丁。源码原生兼容 HarmonyOS。

## 依赖版本

无外部依赖。openbsd-compat 提供缺失函数（getprogname, strtonum）。

## 验证结果

```bash
# 二进制类型
file table-socketmap
# ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped

# 功能测试：发送 config|ready 协议握手
echo "config|ready" | ./table-socketmap /tmp/nonexistent.sock
# 输出: register|alias / register|domain / ... / register|ready
```

## 注意事项

- 源码 tarball 不含生成的 configure 脚本，conanfile.py build() 中需运行 autoreconf -vfi
- 二进制安装到 libexec/smtpd/ 目录（通过 Makefile.am install-exec-local）
- getprogname() fallback 返回 "table-passwd"（上游代码问题，不影响功能）
---

**编译结束**: 2026-08-17 16:54
**最终状态**: built

## COMPLETED
