# libbacktrace

## 简介
libbacktrace 是 GCC/libiberty 系的 C 库，为 ELF、Mach-O、XCOFF、PE-COFF 程序生成符号化回溯（文件名/行号/函数名），支持压缩调试段（zlib/zstd/xz）、DWARF-5 与 build-id 查找。上游快照 20240505 对应 ianlancetaylor/libbacktrace 提交 11427f3。

## OHOS 适配
- **构建系统**: autotools，最小参数 `--prefix`，默认静态库
- **平台识别**: config.guess/config.sub 补 `aarch64-unknown-linux-ohos`
- **HMDFS**: configure 私有临时目录 umask 077 → 022（E129）
- **测试栈帧**: `-fno-optimize-sibling-calls -fno-omit-frame-pointer`（clang 忽略 noclone）
- **签名**: objcopy 派生测试产物按 remove-section → selfSign → chmod 流程重签名（E077）

## 依赖
- zlib 1.3.1（仅上游 ztest 链接使用）

## 功能验证
```bash
make check   # 33 项上游测试全量通过
```
