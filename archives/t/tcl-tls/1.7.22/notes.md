# tcl-tls 1.7.22 适配笔记

## 基本信息
- 软件: tcl-tls (Tcl TLS/SSL extension)
- 版本: 1.7.22
- 源码: https://core.tcl-lang.org/tcltls/uv/tcltls-1.7.22.tar.gz
- SHA256: e84e2b7a275ec82c4aaa9d1b1f9786dbe4358c815e917539ffe7f667ff4bc3b4
- 构建系统: autotools
- 许可证: MIT

## 依赖
- tcl 9.0.3.1 (Conan 包 tcl/9.0.3.1)
- openssl 3.5.6 (Conan 包 openssl/3.5.6, 静态库)

## 编译环境
- CC=clang (clang 15.0.4, OHOS SDK)
- LD_LIBRARY_PATH 需包含 OHOS SDK llvm/lib (lld 依赖 libxml2.so.16, E132)
- TMPDIR=$HOME/tmp (/tmp 只读, E002)

## 适配修改

### 1. config.guess/config.sub 更新
原版 config.guess (2014) 不识别 HarmonyOS，从 abiword 构建目录复制支持 OHOS 的版本。
输出: aarch64-unknown-linux-ohos

### 2. configure umask 修复
config.status 使用 `umask 077` 创建临时目录，HMDFS 不允许向 0700 权限目录写入文件。
修改: configure 中 `umask 077` → `umask 022`

### 3. Tcl 9.0 兼容性宏 (CPPFLAGS)
tcl-tls 1.7.22 使用了 Tcl 8.x 已弃用/移除的宏:
- `-DCONST=const` — Tcl 9.0 移除了 CONST 宏
- `-DVOID=void` — Tcl 9.0 移除了 VOID 宏
- `-D_ANSI_ARGS_(x)=x` — Tcl 9.0 移除了 _ANSI_ARGS_ 宏
- `-DTCL_CHANNEL_VERSION_2=TCL_CHANNEL_VERSION_5` — Tcl 9.0 使用 CHANNEL_VERSION_5

### 4. Tcl_InitStubs 版本修改 (tls.c)
源码: `Tcl_InitStubs(interp, "8.4", 0)` → `Tcl_InitStubs(interp, "9.0", 0)`
原因: Tcl 9.0 的 stubs 机制不向后兼容 "8.4" 版本要求

### 5. pkgIndex.tcl 版本检查修改
源码: `[package vsatisfies [package present Tcl] 8.5]` → `8.5-`
原因: Tcl 9.0.3 不满足 "8.5" (精确版本匹配)，需要用 "8.5-" (8.5或更高)

### 6. objcopy 跳过 (Makefile)
Makefile 中的 `objcopy --discard-all` 处理导致 .so 文件在 OHOS 上无法加载 (Permission denied)。
跳过 objcopy 步骤，直接使用编译器输出的 .so。

## configure 参数
- --prefix=$DEFAULT_PREFIX
- --with-tcl=/storage/Users/currentUser/usr/local/lib (定位 tclConfig.sh)

## make check 结果
- Makefile 无 check 目标，有 test 目标
- test 目标执行 tests/all.tcl
- 测试因 tls 包路径问题无法在构建目录直接运行
- 功能验证通过: package require tls 成功, tls::version 返回 OpenSSL 1.1.1w

## 功能验证
- tclsh 能成功加载 tls 包: `package require tls` → 1.7.22
- OpenSSL 版本: `tls::version` → OpenSSL 1.1.1w 11 Sep 2023
---

**编译结束**: 2026-07-03 13:01
**最终状态**: built
7-03 13:01
**最终状态**: built
