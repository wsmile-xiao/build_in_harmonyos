# LuaJIT

LuaJIT 是一个即时编译（JIT）的 Lua 解释器，性能比标准 Lua 解释器高出 5-10 倍。

## 基本信息

- **软件名称**: LuaJIT
- **官网**: https://luajit.org/
- **许可证**: MIT
- **类型**: 编程语言/解释器

## 版本说明

LuaJIT 使用 rolling release 模式，版本号基于最新 git commit 时间戳生成。

## 特性

- JIT 编译器：将 Lua 代码编译为优化的机器码
- FFI 库：直接调用 C 函数和访问 C 数据结构
- 高性能：比标准 Lua 快 5-10 倍
- 完全兼容 Lua 5.1 语言规范
- 64 位支持（GC64 模式）

## OHOS 适配说明

### 已解决问题

1. **编译器适配**：使用 clang 替代 gcc（系统无 gcc）
2. **mremap syscall**：OHOS 不支持 mremap，已禁用相关功能
3. **/tmp 只读问题**：改用 $TMPDIR 或 /data/local/tmp

### 补丁列表

- `0001-src-Makefile.patch`：将 DEFAULT_CC 从 gcc 改为 clang
- `0002-src-lib_os.c.patch`：修复 os.tmpname 的 /tmp 硬编码
- `0003-src-lj_alloc.c.patch`：禁用 mremap（OHOS 不支持）
- `0004-src-lj_trace.c.patch`：修复 perf map 文件的 /tmp 硬编码