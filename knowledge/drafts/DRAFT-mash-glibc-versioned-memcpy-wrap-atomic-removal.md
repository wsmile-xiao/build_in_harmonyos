# glibc 版本化 memcpy 与 ld `--wrap` 必须一起处理

## 适用范围与症状

一些旧 C/C++ 上游为兼容 glibc 的老 `memcpy` ABI，在所有非 Darwin
构建里强制注入 `.symver memcpy,memcpy@GLIBC_2.2.5`，同时用
`-Wl,--wrap=memcpy` 和 `__wrap_memcpy` 包装函数。目标 libc 若不是 glibc
（例如 aarch64 OHOS musl），只导出普通 `memcpy`，编译可以全过，最终
链接才失败：

```text
ld.lld: error: undefined symbol: memcpy@GLIBC_2.2.5
>>> referenced by memcpyWrap.c
>>>               src/mash/memcpyWrap.o:(__wrap_memcpy)
>>> referenced by CommandScreen.cpp
>>>               CommandScreen.o:(mash::CommandScreen::run() const) in archive libmash.a
```

触发实例为 Mash 2.3 任务 #8702。上游 `src/mash/memcpyLink.h` 只有
`.symver` 语句；`src/mash/memcpyWrap.c` 的 `__wrap_memcpy()` 又调用
`memcpy()`；`Makefile.in` 同时向 C/C++ 编译注入该头，并在链接阶段给
`--wrap=memcpy` 与 `memcpyWrap.o`。四个位置组成同一条兼容路径。

## 根因与反证

原始构建对象的未定义符号：

```text
$ llvm-nm -u src/mash/memcpyWrap.o src/mash/CommandScreen.o | grep memcpy
                 U memcpy@GLIBC_2.2.5
                 U memcpy@GLIBC_2.2.5
```

OHOS 的 libc 导出普通 `memcpy`，没有 glibc 版本节点，故不能通过简单
加链接库解决。仅删 `.symver` 也不安全：`--wrap=memcpy` 会把包装函数
内部的普通 `memcpy` 再映射到 `__wrap_memcpy`。为验证这个独立于 Mash
算法的机制，在设备上编译最小 C 探针（`-O0 -fno-builtin-memcpy
-Wl,--wrap=memcpy`）：

```c
static volatile int calls;
void *__wrap_memcpy(void *d, const void *s, size_t n) {
    if (++calls >= 4) _exit(42);
    return memcpy(d, s, n);
}
```

主函数调用一次 `memcpy`，实测 `RECURSION_PROBE_RC=42`。这个上限使
探针不会无限递归，却证明“只删版本绑定”不是有效修复。

## 推荐方案

对非 glibc 目标，把该兼容路径**成组移除**：

1. 取消 `-include src/mash/memcpyLink.h`，不再产生
   `memcpy@GLIBC_2.2.5` 引用；
2. 同时取消链接参数 `-Wl,--wrap=memcpy`；
3. 从链接对象和构建规则中移除 `memcpyWrap.o`；
4. 让普通 `memcpy` 直接由目标 libc 提供，并运行上游功能测试。

Mash 的补丁为 `patches/0001-remove-glibc-versioned-memcpy-wrapper.patch`。
补丁后 `llvm-nm -u libmash.a | grep memcpy` 只显示普通 `U memcpy`，
`memcpyWrap.o` 不再构建；`make test` 中 `genomes.json`、`reads.json`、
`genomes.dist`、`screen` 四项参考结果比对全部通过，安装后二进制的
消费者检查 5/5 通过。这说明移除兼容路径没有损坏 Mash 的拷贝语义。

## 边界与查重

- 对真正要运行在老 glibc 上的二进制，不能无条件套用 OHOS 补丁；应保留
  老 ABI 兼容方案并在该目标上另测。这里的适用前提是**非 glibc libc**。
- E104 处理的是链接器找不到版本脚本文件，尚未发生 ELF 符号版本解析；
  本条是对象明确引用 `GLIBC_2.2.5` 而目标 libc 无此版本。
- E531 是 `qsort_r` 的 GNU/BSD 函数签名差异；本条函数签名不变，失败来自
  `.symver` 与 `--wrap` 这对 ELF 链接机制。
- E368 的 `--wrap` 用于 Meson 故障注入测试，不涉及 glibc 符号版本或
  包装函数自递归。
- Issue #3408 / `DRAFT-libfaketime-0.9.11-musl-symver-alias` 处理的是
  LD_PRELOAD 时间函数**拦截器**：删去 `.symver` 后还必须以 alias 导出
  同名公开入口，否则功能静默丢失。Mash 的 `memcpyWrap.o` 仅为旧 glibc
  `memcpy` ABI 兼容包装，不向用户提供拦截 API；成组移除后普通 libc
  `memcpy` 可直接完成原语义，且上游 4/4 与消费者 5/5 实测通过。因此
  “整组移除”只适用于这种**冗余兼容包装**，不能套到仍承担功能的 interposer。
- 当前 `main` 的 `knowledge/graph`、`knowledge/drafts`、`knowledge/doc`
  对 `GLIBC_2.2.5`、`.symver `、`--wrap=memcpy` 精确检索均为 0 命中。

## 证据与元信息

- 触发任务：`mash 2.3`，平台任务 #8702；上游 tag `v2.3`，源码 tarball
  SHA-256 `f96cf7305e010012c3debed966ac83ceecac0351dbbfeaa6cd7ad7f068d87fe1`。
- 原始链接失败、补丁后上游 4/4、消费者 5/5 均在 aarch64 OHOS 真机的
  `conan create` 中实测；独立递归探针同机 rc=42。
- 作者与贡献者 ID：`frj__`；本文件为待评审草稿。
