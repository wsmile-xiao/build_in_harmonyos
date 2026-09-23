# libc-abi (libc++abi)

LLVM 的 C++ ABI 库，即 [libcxxabi](https://libcxxabi.llvm.org) 子项目。它是
libc++ 的 ABI 底座，实现 C++ 运行时中与具体标准库实现无关的那部分：
`__cxa_*` 符号族。

## 提供的能力

| 能力 | 关键符号 |
|------|---------|
| 异常抛出 / 捕获 / 栈展开 | `__cxa_throw`、`__cxa_begin_catch`、`__cxa_end_catch`、`__cxa_rethrow`、`__cxa_allocate_exception`、`__cxa_free_exception` |
| 依赖异常（dynamic_cast 失败、纯虚调用） | `__cxa_bad_cast`、`__cxa_bad_typeid`、`__cxa_pure_virtual` |
| RTTI | `__dynamic_cast`、`__cxa_type_match`、`type_info` 支撑 |
| 符号反修饰 | `__cxa_demangle` |
| 函数内静态量线程安全初始化 | `__cxa_guard_acquire`、`__cxa_guard_release`、`__cxa_guard_abort` |
| 线程局部对象的析构 | `__cxa_thread_atexit`、`__cxa_thread_atexit_impl` |
| 默认 `operator new` / `delete`（含对齐与数组重载） | `_Znwm`、`_Znam`、`_ZdlPvm`、`_ZdlPvSt11align_val_t` 等 |

## 与设备的关系

设备 OHOS SDK 自带 `libc++abi.a`（**版本 15**）。本包是**系统同名库**，按铁律
R26 只构建/安装**静态库**，不产出任何 `.so`，避免污染设备 `/lib`、`/lib64`。
配方内 `_check_no_shared()` 在打包阶段守卫该约束（发现 `.so` 即报错）。

因此消费方必须显式链接本包，链接顺序上把本包的 `libc++abi.a` 放在 SDK
`libc++.a` **之前**，`__cxa_*` 才会由本包提供。

## 头文件来源（重要）

libcxxabi 自身只提供两个头文件：`cxxabi.h`、`__cxxabi_config.h`（安装到
`include/c++/v1/`）。而它的**构建**需要一份 libc++ 头文件。

本仓库 22.1.8 源码树自带的 libc++ 22 头文件要求 **clang 19+**，而设备/CI 工具链
是 **clang 15**，无法直接使用；故本配方改用 OHOS SDK 随附的 **libc++ 15** 头文件
（经 `-isystem` 注入），并把 libcxxabi 22 源码对该 libc++ 版本的差异收敛为
`patches/0001`–`patches/0008`（共 8 个补丁，逐条见版本目录 `conandata.yml`
的 `patches` 清单）。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 22.1.8 | built | 首次适配，随 LLVM 22.1.8 单仓发布 |

> libc++abi 没有独立 tarball，源码取自 LLVM 单仓
> `llvm-project-22.1.8.src.tar.xz`（与 `archives/c/clang/22.1.8` 同源）。

## 上游

- 主页：<https://libcxxabi.llvm.org>
- 源码：<https://github.com/llvm/llvm-project>
- 许可证：Apache-2.0 WITH LLVM-exception
