# DRAFT-ohos-kernel-annotation-macros — OHOS sysroot 内核风格头 __user 等注解宏缺失

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-03
> **Severity**: 🟡 medium | **Category**: ohos / musl / kernel-headers / compilation

## 相关既有条目（同族差异化定位）

本 skill 与既有 "musl libc 缺失" 及 "gettext 编译期" 条目共享 OHOS musl 兼容层背景，
但本条目是 **内核 uapi 头注解宏缺失**——非重复条目；申报路径 B 时以此差异化定位为准。

| 既有条目 | 收录状态 | 问题面 | 本 skill 的增量（差异化） |
|---------|---------|--------|--------------------------|
| **E081**（secure_getenv） | 正式收录 | musl 无 secure_getenv（glibc 扩展函数） | 非本题——那是**函数缺失**，本条目是**宏缺失**（__user 等注解宏，空宏定义即修复） |
| **E493**（program_invocation_name） | 正式收录 | musl 无 program_invocation_name（glibc 符号） | 非本题——那是**符号缺失**，本条目是**头文件注解宏**；问题层完全不同 |
| **DRAFT-ohos-autotools-rpl-malloc**（speech-dispatcher） | 草稿 | autotools 交叉编译 AC_FUNC_MALLOC 误判 | 非本题——那是 **configure 缓存变量**，本条目是**编译期宏定义** |
| **E041/E071**（automake 缺失） | 正式收录 | automake 工具缺失 | 非本题——那是**构建工具**，本条目是**uapi 头宏** |

> 全库查证（2026-09-03）：`__user`/`__force`/`__iomem`/内核注解宏/mtd-abi 命中 0 条——
> 无正面撞车；本条目为真增量。

## Scope（何时用）

在 OHOS 上编译任何**间接 include 了带内核注解宏的 uapi 头**的库/工具时，若出现：

- 编译报 `expected ';' at end of declaration list`（如 `unsigned char __user * ptr;`
  中 `__user` 未定义被当普通标识符）；
- 报错头位于 sysroot（如 `<mtd/mtd-abi.h>`）；
- 已确认 OHOS musl libc 不定义 `__user/__force/__iomem/__kernel` 这些内核注解宏。

典型实例：systemd/261 编译 `mtd_probe`（`mtd-abi.h:33` 报错）。

## Symptom

```text
mtd-abi.h:33:23: error: expected ';' at end of declaration list
  unsigned char __user * ptr;
              ^
# __user 未定义 → 编译器把 __user 当标识符，后续 * ptr 无法解析
```

## Root Cause

1. Linux uapi 头（如 `mtd/mtd-abi.h`、部分 syscall 接口头）为配合 sparse 静态
   分析用 `__user/__force/__iomem/__kernel` 注解指针/参数；
2. glibc 工具链通常经 `linux/compiler.h` 或预定义提供这些宏；
3. OHOS sysroot 直接暴露这些头给用户态，但 OHOS 的 **musl libc 不定义**这些宏——
   编译含这类头的 .c 时把 `__user` 当普通标识符 → `expected ';'` 语法错。

## Recommended Solution

**主方案：编译参数给注解宏加空定义**（与内核编译时 sparse 关闭的空宏一致）：

```python
# conanfile.py meson/AutotoolsToolchain c_args 中
for k in ("__user", "__force", "__iomem", "__kernel"):
    c_args.append(f"-D{k}=")
```

一条 c_args 解决，零补丁、零源码改动。

**回退方案**：若编译参数注入不可行，patch 源码中直接 include 的内核头去掉
`__user` 等注解（或提供空宏定义头）——改动面大，不推荐。

## 单库实证

| 库 | 角色 | 结果 |
|----|------|------|
| **systemd/261** | 主验证（本 PR） | ✅ 覆盖前 mtd_probe 编译报 `mtd-abi.h:33 expected ';'`；加 `-D__user=` 等空宏定义后编译通过，conan create 通过 |

## 测试覆盖边界

- 空宏定义是**编译期**兼容层：只消除 uapi 头注解宏对用户态编译的干扰，不改
  任何源码语义（这些宏在用户态本就无实际作用）；
- 声明通过率时：以 conan create 全流程（libsystemd.so.0.44.0 链接 + test_package
  R34）为实证；systemd 上游测试按 rule 1.2 平台限制声明（需运行中的 systemd 环境）。
