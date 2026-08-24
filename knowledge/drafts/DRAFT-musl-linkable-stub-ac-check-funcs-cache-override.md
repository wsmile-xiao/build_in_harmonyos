# DRAFT-musl-linkable-stub-ac-check-funcs-cache-override：musl 可链接桩无 struct 的 AC_CHECK_FUNCS 误判

> Contributor: i686-elf-binutils 2.46.1 适配 | Status: Draft | Updated: 2026-08-23
> Source: archives/i/i686-elf-binutils/2.46.1

## 现象

binutils 的 ld 在 musl 上 configure 阶段链接级 AC_CHECK_FUNCS 探测 mallinfo/
mallinfo2 全部"通过",但 ldmain.c 在 struct mallinfo 上编译失败 (incomplete type)。

## 根因分析

- musl 把 glibc 专属 malloc 统计 API (mallinfo/mallinfo2) 作为可链接兼容桩导出,
  但不在 <malloc.h> 定义对应 struct。
- autoconf 链接级 AC_CHECK_FUNCS 只做链接探测 → 符号存在 → HAVE_MALLINFO(_2)=1。
- 源码按完整类型编译 → incomplete type 失败。

## 解决方案

build() 用缓存覆盖让 autoconf 判该 API 缺失,ld 跳过可选 malloc 统计:

```python
os.environ["ac_cv_func_mallinfo"] = "no"
os.environ["ac_cv_func_mallinfo2"] = "no"
```

## 跨库复用证据

- i686-elf-binutils 2.46.1 (本候选)、x86_64-elf-binutils 2.46.1、
  riscv64-elf-gdb 17.2 三处注释+修复同款。
- 适用:GNU 工具链族及 musl/OHOS 上的 autotools 项目。

## 验证证据

- round-5 full.log L2787 "checking for mallinfo... (cached) no"、L2790
  "checking for mallinfo2... (cached) no" → 缓存覆盖实际生效。
- round-5 make check 0 unexpected failure (2244 pass),无 HAVE_MALLINFO 相关编译错误。

## 禁止做法

- 不要用 __OHOS__ 平台宏或 #define HAVE_MALLINFO 预置答案。
- 不要保留链接级 AC_CHECK_FUNCS(mallinfo) 探测 (仍会误判)。

## 知识库查重结论

- 最相近条目 E320 (fmemopen 链接成功但运行时 EBADF,AC_RUN_IFELSE 运行时探测)、
  E302/E230 (同族链接级检测误导):均为链接级检测误导家族,但本条是"编译期类型缺失 +
  缓存覆盖",修复路径不同,宜独立条目并与 E320/E302/E230 互链。
- 检索词 mallinfo / HAVE_MALLINFO / ac_cv_func / linkable / incomplete type 在
  knowledge/graph+drafts+doc+operations 全目录 grep 无对应条目 (musl 文档仅作
  glibc 特有 API 分类表)。
- 无既有条目覆盖,本条目为新增候选。

## 关联条目

- 相关: E320、E302、E230
