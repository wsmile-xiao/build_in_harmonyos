# catdoc 1.0.0 适配说明

## 基本信息

- **源码**: [petewarden/catdoc](https://github.com/petewarden/catdoc) (master 分支, upstream 版本 0.94.2)
- **构建系统**: Autoconf + hand-written Makefile.in (无 automake)
- **包类型**: application (命令行工具)
- **许可证**: GPL-2.0-only

## OHOS 适配要点

### R8: clang-15 优化 bug (SIGSEGV)

**现象**: catdoc 二进制在 OHOS aarch64 上运行时, 在 main() 之前 SIGSEGV.

**根因**: clang-15 对 fileutil.c 中的 glob/path 处理代码在 -O1 及以上优化级别产生错误代码. 通过逐文件编译二分定位确认: 只有 fileutil.c 在 -O1 编译时导致崩溃, -O0 正常.

**修复**:
1. `tc.extra_cflags = ["-O0", ...]` 注入到 AutotoolsToolchain
2. Python 文件 I/O 直接修补 configure 脚本中的所有 `-O2` 为 `-O0`

### R9: 旧式 C 代码警告

catdoc 源码来自 1994 年, 大量使用隐式函数声明、隐式 int、类型不匹配等.
通过 `tc.extra_cflags` 添加 `-Wno-error-*` 标志.

### 构建系统

- 使用 `configure.in` (非 `configure.ac`), autoheader 2.13
- 手写 Makefile.in, 不使用 automake
- `--prefix=/` 使 CHARSETPATH 编译为 `/share/catdoc`
- `installroot` 变量控制安装目标目录 (非 DESTDIR)

## 构建命令

```bash
conan create archives/c/catdoc/1.0.0 -pr:h ohos-aarch64 -pr:b default --build=missing
```

## 测试结果

- `catdoc -V` → "Catdoc Version 0.94.2" ✅
- `xls2csv -V` → "Catdoc Version 0.94.2" ✅
- `catppt -V` → "Catdoc Version 0.94.2" ✅
- `catdoc` (无参数) → 运行不崩溃 (charset 未找到是预期行为) ✅
- `catdoc -l` → 运行不崩溃 ✅

## 已知限制

1. 字符集文件安装在 `/share/catdoc`, 运行时需要 `.catdocrc` 配置文件指定实际路径
2. `-O0` 编译, 无优化 (clang-15 bug)
3. wordview (Tk GUI) 已禁用
