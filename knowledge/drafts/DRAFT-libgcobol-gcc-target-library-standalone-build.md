# DRAFT-libgcobol-gcc-target-library-standalone-build — GCC target library 在 OHOS 上的独立构建

> **状态：** `draft: true`
> **来源：** libgcobol 16.1.1 R01 真机 shadow CI 适配（OHOS/AArch64）
> **验证对象：** libgcobol/16.1.1（conan create + test_package，真机 shadow CI exit 0）
> **关联条目：** E012（找不到 llvm-ar）、E011/E052/E060（config.status HMDFS 临时目录）、E046/E087（HMDFS 无执行位）、E004（运行时符号加载）
> **非重复声明：** 本条覆盖「GCC target library 独立构建」的完整链路（选择性解压 + HMDFS configure + LLVM 工具链 + C23 类型 + compiler-rt 链接），该组合未被任何已有正式条目或草稿覆盖。

## 问题

libgcobol 是 GCC 16 的 COBOL 运行时库（target library，与 libgomp/libstdc++ 同级），无独立 release tarball。在 OHOS/AArch64 上独立构建时，依次遇到 9 类失败：

| 阶段 | 症状 | 根因 |
|------|------|------|
| source | `No space left on device` (Errno 28) | 解压整个 2 GB GCC 树耗尽 HMDFS 磁盘 |
| configure | `configure: Permission denied` | HMDFS 解压后 configure 丢失 +x 且 chmod 不生效 |
| configure | `cannot find install-sh` | 树根 autotools 辅助脚本未随子目录提取 |
| configure | `no acceptable ld found` | OHOS 仅有 LLVM 工具链，无裸名 ar/nm/ranlib/ld |
| config.status | `subs1.awk: Permission denied` | HMDFS 上 `mktemp -d "./confXXXXXX"` 失败 |
| compile | `unknown type name '_Float32'` | C23 浮点类型在 clang++（C++ 模式）下不存在 |
| link | `unable to find library -lgcc` | OHOS clang 无 libgcc.a，用 compiler-rt builtins |
| runtime | `__divti3: symbol not found` | 128-bit 运算辅助符号未链接 |
| configure | `Link tests are not allowed after GCC_NO_EXECUTABLES` | 链接库加在 configure 阶段破坏 conftest |

## 根因

GCC target library 深度耦合 GCC 树：configure 依赖 `../gcc/BASE-VER` 与树根 aux 脚本（install-sh/config.guess/config.sub），源码必须保留 GCC 树目录上下文；而 OHOS 环境叠加了 HMDFS 权限限制、LLVM-only 工具链、C++ 编译器的 C23 类型差异、compiler-rt（非 libgcc）链接模型，形成一条普通 C/C++ autotools 配方无法直接复用的构建链路。

## 修复方案

在 `conanfile.py` 中逐项闭环（见 `archives/l/libgcobol/16.1.1/conanfile.py`）：

1. **选择性解压**：`source()` 用 `download()` + `tarfile`，只提取 `libgcobol/` + `gcc/BASE-VER` + 树根直接文件（139 个 member，约数 MB）。
2. **configure 执行**：`/bin/sh configure`（HMDFS 无执行位）。
3. **LLVM 工具链注入**：export `AR=llvm-ar NM=llvm-nm RANLIB=llvm-ranlib LD=ld.lld` 等绝对路径。
4. **config.status 临时目录**：patch configure `mktemp -d "./confXXXXXX"` → `mktemp -d "$TMPDIR/confXXXXXX"`，设 `TMPDIR=/data/storage/el2/base/cache`。
5. **C23 类型替换**：patch libgcobol.cc `_Float32`→`float`、`_Float64`→`double`。
6. **compiler-rt 链接**：make 阶段 `LIBS='-lclang_rt.builtins'`（不可加在 configure 阶段，否则触发 GCC_NO_EXECUTABLES）。
7. **依赖源**：shadow job 手动加 ohpcd remote 命中仓库 `libxml2/2.15.3` 预编译 OHOS 二进制。

## 验证

1. 真机 shadow CI `conan create` exit code 0，`Total: 1 / Success: 1 / Failed: 0`。
2. test_package 3 条真实计算断言通过：`__gg__power_of_ten(2)=100, (0)=1, (5)=100000`。
3. L0/L1/L4/L5 全 pass（L1 含 L1e 破坏性负测试），L2 skip（库包无 bin/）。

## 适用边界

- **适用：** GCC 16 target library（libgcobol/libobjc 等）在 OHOS/AArch64/musl 上的独立 Conan 构建；其他无独立 tarball、需从父项目源码树选择性提取子目录的库。
- **不适用：** 有独立 release tarball 的常规 autotools 库；含需要 GCC 前端编译的子库（如 libgcobol 16.1.0 之后的 posix/compat COBOL 子库仍需 GCOBOL 前端）。
- **已知限制：** 完整上游测试（`make check-cobol`）需 GCOBOL 前端；本包以 test_package 消费断言验证。

## 原始证据

- 配方：`archives/l/libgcobol/16.1.1/conanfile.py`
- 笔记：`archives/l/libgcobol/16.1.1/notes.md`
- 真机 run 目录：`codex-16.1.1-libgcobol-16.1.1-shadow-20260921-204917-conan-20260922-001719-8947`（logs/exit-code.txt = 0）
