# DRAFT-13904：OHOS 上 JIT 代码缓存不能用 memfd+PROT_EXEC（swiftshader / Reactor）

> Status: **Draft**（待审核 promote）| severity: `P0` | category: `platform` | Updated: 2026-09-30
> 对应: `knowledge/drafts/DRAFT-13904-swiftshader-ohos-jit-memfd-exec-memory.kv`
> 来源 PR: #13904（swiftshader 0_git20260921 适配 HarmonyOS PC）

---

**匹配关键词**：memfd_create, PROT_EXEC, EACCES, Permission denied, JIT, executable memory, SIGILL, SIGSEGV, LLVMJIT, Reactor, MAP_ANONYMOUS

## 错误签名（error_signature）

```text
SIGSEGV|SIGILL during JIT execution.*memfd_create.*PROT_EXEC|mmap.*Permission denied|MapFailed
```

## 错误摘录（error_excerpt）

最小探针（OHOS PC aarch64，clang15/musl）：

```text
page=4096
[1] anon RWX mmap: ok (errno=0 ) ptr=0x5e95d3d000
    calling...
    anon call -> rc=7                       # 匿名 RWX 内存可执行（mov w0,#7; ret 返回 7）
[2] memfd_create: ok fd=3 (errno=0 )
    mmap RWX: FAILED (errno=13 Permission denied) ptr=0xffffffffffffffff
```

被测软件现象：SwiftShader 的 Reactor JIT 在 OHOS 上全部单测 SIGSEGV/SIGILL
（`ReactorSIMD.Add` 崩溃，`vk-unittests` 计算套件无法运行），而匿名可执行映射本身是好的。

## 根因（root_cause）

OHOS 内核/安全策略**拒绝把 `memfd_create()` 创建的文件以 `PROT_EXEC` 映射**（`mmap` 返回 `MAP_FAILED`，errno=EACCES）。
JIT（LLVM MCJIT / Reactor / 任何运行期生成机器码的组件）若按 Linux 常见做法用 memfd 命名代码页，
在 OHOS 上会拿到空映射 → 写入或跳转生成代码即崩溃。
匿名 `mmap(PROT_READ|PROT_WRITE|PROT_EXEC, MAP_PRIVATE|MAP_ANONYMOUS)` **允许**且可执行。

## 推荐方案（rec_approach）

1. 先用三步探针区分根因（不要凭猜）：
   (a) 匿名 `mmap(RWX)` + 写 `mov w0,#7; ret` + 调用；
   (b) `memfd_create` + `mmap(PROT_EXEC)`；
   (c) `mmap(RW)` + `mprotect(RX)` + 调用。
2. 在 JIT 侧按平台分支：`#if defined(__OHOS__)` 用 `MAP_ANONYMOUS`（不做 memfd 命名），
   其余平台沿用原逻辑。
3. 同步用 `!defined(__OHOS__)` 收口因此不再被引用的 memfd 帮助函数，
   否则 `-Wunused-function` 在 `-Werror` 下直接编译失败。

参考实现（swiftshader `src/Reactor/ExecutableMemory.cpp`，patches/0004）：

```cpp
	int flags = MAP_PRIVATE;
#if defined(__OHOS__)
	int anonFd = -1;
	flags |= MAP_ANONYMOUS;
#else
	int anonFd = anonymousFd();
	if(anonFd == -1) { flags |= MAP_ANONYMOUS; }
	else { ensureAnonFileSize(anonFd, length); }
#endif
	mapping = mmap(nullptr, length, permissionsToMmapProt(permissions), flags, anonFd, 0);
```

效果：`ReactorUnitTests` 155/156、`vk-unittests` 计算套件 136/136 全绿。

## 适用范围

任何在 OHOS 上运行"运行期生成/加载机器码"的库：JIT 引擎（LLVM/Subzero/V8/SpiderMonkey/JSC）、
`dlopen` 自己生成的 .so、自解压/自修改代码、部分语言运行时（Graal、.NET dynamic、LuaJIT）。
凡源码里出现 `memfd_create` + `PROT_EXEC` 组合，都应先在本平台跑三步探针。

---

*本文件由 `knowledge/drafts/DRAFT-13904-swiftshader-ohos-jit-memfd-exec-memory.kv` 字段派生生成（补齐 kv↔md 配套）；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*
