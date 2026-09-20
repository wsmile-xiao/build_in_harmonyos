# DRAFT-gperftools-emutls-tls：gperftools 1.6 OHOS emutls 惰性 TLS 递归崩溃与 -fno-emulated-tls 修复

> Contributor: oh-executor pc2-7 | Status: Draft | Updated: 2026-09-10
> Source: PR 【知识库扩展】feat(gperftools) perftools-1.6 适配

## 背景

gperftools 1.6（tcmalloc）在 HarmonyOS PC 真机适配时，构建全绿（大量
C++17/架构补丁后），但任何链接该库的二进制在 main() 之前以 Signal 11 崩溃，
且手动与 conan 干净构建均复现。崩溃位于库静态初始化期，首个 malloc 之后的
第二次分配无限递归。

## 根因

OHOS 工具链 clang（target aarch64-unknown-linux-ohos）默认把 `__thread`
编译为 **emulated TLS（emutls）**：TLS 变量的访问被替换为对
`__emutls_get_address` 的运行时调用，该函数在**首次访问**该 TLS 变量时通过
malloc() 惰性分配 TLS 块。对 tcmalloc 这类替换 malloc 的分配器：

```
TCMallocGuard 构造 → tc_malloc(1) → ThreadCache::GetCache()
  → 读 threadlocal_heap_（__thread）
  → __emutls_get_address() → malloc()
  → tcmalloc do_malloc → GetCache() → 再次读 threadlocal_heap_
  → __emutls_get_address() → malloc() → …… 无限递归
```

栈被耗尽，进程以 Signal 11（SEGV）死在 main 之前。诊断特征：
`GetCache depth=N` 单调增长、preload SIGSEGV 处理器 frames=0、
`__emutls_t._ZN8tcmalloc11ThreadCache17threadlocal_heap_E` 符号出现在
动态符号表。

## 方案

编译全链路加 `-fno-emulated-tls`：编译器生成真 TLS（TLSDESC 重定位），
TLS 块由 loader 在加载时分配，首次访问不再调用 malloc，递归消除。
Conan 配方（AutotoolsToolchain）注入方式：

```python
tc.extra_cxxflags.append("-fno-emulated-tls")
tc.extra_cflags.append("-fno-emulated-tls")
```

必须用 `extra_*flags`（写入 toolchain 脚本 CXXFLAGS 行）；`cxxflags`
（env 注入）在部分 conan 版本未落入 configure 环境。

## 验证

- 干净 `conan create` 全绿：conan-verify G0/G1/G2/G3/G4/L2/L4/L5 全 PASS。
- `nm -u` 不再出现 `__emutls_get_address`。
- 本地静态构建 `make check`：36 项测试中 20 项 PASS（其余为 /tmp 只读
  平台限制与测试环境差异，见回报台账）。

## 适用边界与反例

- 适用：OHOS/musl 上编译**替换 malloc 的分配器**（tcmalloc/jemalloc 系）。
- 反例：glibc x86_64 等原生 TLS 平台无需；不替换 malloc 的普通库通常
  不触发递归，但惰性分配语义仍应知晓。
- 该 flag 会改变 TLS 模型（TLSDESC），对依赖初始-exec/局部执行模型的
  场景需另行评估。
