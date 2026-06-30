# ripmime 1.4.1.0 — 归档摘要

## 基本信息

| 字段 | 值 |
|------|-----|
| 软件 | ripmime |
| 版本 | 1.4.1.0 |
| 状态 | published |
| 构建系统 | makefile |
| 编译日期 | 2026-06-09 |
| 编译器 | clang/clang++ |
| 架构 | aarch64 (OpenHarmony) |

## 源码信息

- **下载地址**: https://github.com/inflex/ripMIME/archive/refs/tags/1.4.1.0.tar.gz
- **SHA256**: 6d551d6b65b4da6c6b8dfd05be8141026cc760ca1fb8a707b7bf96c199c9f52d

## 补丁（4个）

| 补丁 | 修改文件 | 说明 |
|------|----------|------|
| 0001-Makefile.patch | Makefile | LOCATION/DESTDIR/LDFLAGS/strip修改 |
| 0002-build_ripOLE.patch | build_ripOLE | 脚本改为只编译.o文件 |
| 0003-ripOLE-Makefile.patch | ripOLE/Makefile | CFLAGS添加-fPIC |
| 0004-tnef-Makefile.patch | tnef/Makefile | PLATFORM小端1234, CFLAGS添加-fPIC |

## 关键问题与解决

1. **lld链接器缺失libxml2.so.16** → 使用GNU ld（`-fuse-ld=/data/service/hnp/bin/ld`）
2. **tnef大端序错误** → PLATFORM改为1234（aarch64小端）
3. **ripOLE链接失败** → build_ripOLE改为仅编译.o
4. **二进制Permission denied** → ELF签名（sign-elf）

## 预编译包

| 包名 | 大小 | 说明 |
|------|------|------|
| ripmime-1.4.1.0-ohos-aarch64.tar.gz | 149K | stripped预编译包 |
| ripmime-1.4.1.0-ohos-aarch64-debug.tar.gz | 14K | 含调试符号 |

## 测试验证

- 版本: v1.4.1.0 ✅
- 功能: MIME文本附件提取 ✅、Base64解码 ✅、目录递归 ✅
- 二进制: AArch64 PIE, 小端序, musl libc, ELF签名 ✅
- 测试项: 9项全部通过

## 知识图谱草稿

- E081-draft-CC07: SDK lld链接器缺失libxml2.so.16 → 使用GNU ld替代
- E082-draft-BCA3: HarmonyOS二进制需ELF签名才能执行