# libtasn1 4.21.0 适配笔记

**日期**: 2026-07-15
**状态**: ✅ 适配完成

## 编译环境

- 平台: HarmonyOS (aarch64)
- 编译器: clang 15.0.4
- 构建系统: autotools (configure + make)

## 适配修改

### 1. config.guess 平台检测 (0001)

config.guess 不识别 HarmonyOS 平台。添加 `aarch64:HarmonyOS:*:*` case，映射到 `aarch64-unknown-linux-ohos`。

### 2. configure umask 修复 (0002)

HMDFS 文件系统上，`umask 077` 创建的临时目录会继承父目录的 setgid 位，导致权限为 `drwx--S---`，文件写入失败 (Permission denied)。

将 `umask 077` 改为 `umask 007`，使目录权限为 `drwxrws---`，group 有写权限，文件可正常创建。

影响位置: configure 脚本的 `mktemp -d "./confXXXXXX"` 和 fallback `mkdir "$tmp"` 两处。

### 3. --disable-doc

系统缺少 texinfo (makeinfo)，使用 `--disable-doc` 跳过文档构建。

## 编译结果

- make: ✅ 成功 (仅 1 个 warning: pkix_asn1_tab 缺少 extern 声明)
- make check: ✅ 31/31 测试通过
- make install: ✅ 成功 (lib + src，跳过 doc)

## 产物

- libtasn1.a / libtasn1.so (库)
- libtasn1.h (头文件)
- asn1Parser / asn1Coding / asn1Decoding (命令行工具)
- libtasn1.pc (pkg-config)
