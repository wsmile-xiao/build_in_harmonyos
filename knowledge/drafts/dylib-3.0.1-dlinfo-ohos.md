# DRAFT-dylib-dlinfo-ohos：OHOS musl libc 无 dlinfo(RTLD_DI_LINKMAP) 的符号枚举替代

> Contributor: AtomCode | Status: Draft | Updated: 2026-09-03
> Source: dylib 3.0.1 适配（task dylib-3.0.1-r01-pc4-2-20260902T192109Z，R02 返工修正
>   dylib-3.0.1-r02-pc4-2-20260903T070222Z）

## 问题

dylib 3.0.1（C++11 动态库加载库）在 OHOS PC（aarch64-linux-ohos, clang 15）编译失败：

```text
src/symbols.cpp:241:9: error: use of undeclared identifier 'dlinfo'
    if (dlinfo(handle, RTLD_DI_LINKMAP, static_cast<void *>(&map)) != 0) {
        ^
1 error generated.
```

上游 `symbols()`（枚举已加载库的导出函数）依赖 glibc 独有的
`dlinfo(handle, RTLD_DI_LINKMAP, &map)` 拿到该库的 link_map，再遍历
`map->l_ld` 的 DT_SYMTAB/DT_STRTAB/DT_SYMENT 收集 STT_FUNC 符号。

## 根因

OHOS 的 libc 基于 musl（sysroot 26.0.0.18）：

- `dlfcn.h` 仅声明 `dlopen/dlsym/dladdr/dlvsym`；**无 dlinfo**
- `link.h` 提供 `dl_iterate_phdr()`、`struct link_map { l_addr; l_name; l_ld; l_next; l_prev }`
- 全 sysroot 头文件与 `libdl.a` 均无 dlinfo 符号
- 直接把 dlopen 句柄强转 `struct link_map*` 读取会段错误（实测 SIGSEGV，句柄内部
  布局与 glibc 不兼容；OHOS dladdr(handle) 也返回 0）

## 方案

新增 `#if defined(__GLIBC__)` 分支保留原 dlinfo 路径；`#else`（musl/OHOS）改用
`dl_iterate_phdr` 回调：

1. 对每个已加载对象，从 `PT_DYNAMIC` 程序头定位动态段：
   `dynamic = dlpi_addr + p_vaddr`
2. 遍历动态段解析 `DT_SYMTAB`、`DT_STRTAB`、`DT_STRSZ`、`DT_HASH`、`DT_GNU_HASH`
   —— **注意 `d_un.d_ptr` 是相对加载基址的偏移，必须加 `dlpi_addr` 才是有效地址**
3. **`.dynsym` 条目数必须用可验证的 ELF 边界，不能用 `DT_STRSZ / DT_SYMENT` 推导**
   （字符串表字节数除以符号项字节数无 ELF 语义，可能漏枚举或越界读）：
   - 优先 `DT_HASH`：其布局为 `nbucket(4) + nchain(4) + bucket[] + chain[]`，
     第二个 32 位字 **nchain 即动态符号表条目数**（ELF ABI 定义）
   - 仅 `DT_GNU_HASH`：布局 `nbuckets(4) symoffset(4) bloom_size(4) bloom_shift(4)
     bloom[bloom_size] buckets[nbuckets] chain[]`。**注意 bloom 元素是 `ElfW(Xword)`
     宽（64 位 ELF 为 8 字节），按 uint32_t 读取会错位**；遍历每个 bucket 的链
     （以 `chain[idx - symoffset]` 低 bit 置 1 为链尾）求最大符号索引，
     条目数 = `max(symoffset + 1, max_index + 1)`
   - 两者皆无：条目数不可验证，**拒绝猜测，跳过该对象**（可证明安全，不越界读）
4. 用 `dlsym(handle, name)` 过滤出该 handle 可解析的符号并标记 loadable=true

实测句柄语义：dlopen 句柄不能当 link_map 用；`d_ptr` 相对偏移语义已通过探针验证
（base+d_ptr 正确解析出 libdynamic_lib.so 的函数符号）。

## 验证

- 上游 gtest（R02 实测 2026-09-07，日志
  `/storage/Users/currentUser/tmp/builds/dylib-3.0.1.work/evidence_r02/upstream_tests_r02_full.log`，
  SHA-256 c0d86e248b686162484e168fe355f4c971b97811067c4379215056b2408c05b0）：C++17 全量
  **17/17 通过**（EXIT=0），含 cpp_symbols.loadable/demangle/interface/callback；修复前
  `strsize/symentries` 推导在部分对象上 SIGSEGV（Signal 11）
- HarmonyOS 专项测试（R02 实测 2026-09-07，`tests/ohos_test.cpp` 真实编译运行，日志
  `/storage/Users/currentUser/tmp/builds/dylib-3.0.1.work/evidence_r02/ohos_test_r02.log`，
  SHA-256 d697250dcf8c1b94e533d8e421105d578c9faa41959877477fd501438af88058）：加载真实
  `/system/lib64/platformsdk/libhilog.so`，`symbols()` 枚举 **3962 个符号**、
  `HiLogPrint` 以变参函数指针实际调用成功（rc=72，>=0），demangled 无 `std::__n1::` 残留，
  7/7 PASS，EXIT=0
- conan create（R02 实测 2026-09-07，日志
  `/storage/Users/currentUser/tmp/builds/dylib-3.0.1.work/evidence_r02/conan_create_r02.log`，
  SHA-256 183d300699b70f759ba2a9a2178a65ad6c782d62ecab0507e7affdbf799f2085）：test_package
  1/1 通过，EXIT=0
- W3 本地 CI（R02 实测 2026-09-07，日志
  `/storage/Users/currentUser/tmp/builds/dylib-3.0.1.work/evidence_r02/w3_local_ci_r02.log`，
  SHA-256 a491fc5337f0ddff180f006402779720ffcc920e3d2b0252497f7180ea91e9b2）：L0/L1/L4/L5 全通过，
  100% (1/1)，RC=0

## 适用边界

- 适用于所有依赖 dlinfo 枚举符号的 C/C++ 库在 OHOS/musl 平台的适配
- d_ptr 相对基址语义（+dlpi_addr）对 dl_iterate_phdr 路径通用
- .dynsym 条目数边界：DT_HASH nchain 优先；GNU hash 按 bucket 链求最大索引；
  无哈希表时不猜测、跳过——三者均为可验证/可证明安全处理
- 若目标只是链接期依赖 libdl（-ldl），应查 E013；本条目专指 dlinfo API 缺失

## 查重差异

- index.tsv/E*.kv：无 dlinfo/dl_iterate_phdr 条目（E004 为运行时 dlopen 符号解析、
  E013 为 -ldl 缺失、E019 为库搜索路径——均不同问题域）→ 未命中
- doc/：E247（std::__n1 静态链接传播）、E286（LLVM 插件 dlopen 符号缺失）部分相关
  但不覆盖本候选 → 部分覆盖
- drafts/：无同名/同主题草稿 → 未命中
- 查重结论：未命中（或至多部分覆盖），有新增差异 → 路径 B 候选

## 七轴查重（R02 实测，2026-09-07）

| 轴 | 结论 |
|---|---|
| exact_duplicate | false（无任何既有条目完整覆盖此问题） |
| causal_duplicate | false（E004/E013/E019 根因不同：运行解析/-ldl/搜索路径） |
| trigger_overlap | partial（触发场景「dlopen 符号枚举失败」与 E004 有交叠，但 E004 无 OHOS musl 缺 dlinfo 的解） |
| solution_overlap | true（与 E013 同属「平台缺 glibc API 用等价 API 替代」结构，但具体方案全新） |
| combination_novelty | true（dl_iterate_phdr + DT_HASH nchain/GNU hash 链遍历组合无既有条目） |
| boundary_novelty | true（无哈希表时跳过=可证明安全边界；bloom 宽度陷阱为新增知识） |
| test_migration_novelty | true（专项测试迁移为 OHOS 真实系统库加载，验证 3962 符号枚举） |

## 关系字段

- `similar_to`: E004（运行时 dlopen 符号解析）、E013（-ldl 缺失）、E019（库加载路径）、
  E286（LLVM 插件 dlopen 符号缺失）——均 dlopen/符号相关，侧重点不同
- `caused_by`: （无既有条目）
- `prerequisite_of`: （无）
- `conflicts_with`: （无）

## 覆盖与新增差异（reuse / new_draft 决定）

- 已覆盖部分：E004 覆盖「dlopen 后符号解析失败」的触发场景；E013 覆盖「-ldl 链接缺失」；
  E019 覆盖「库搜索路径」；E286 覆盖「LLVM 插件 dlopen 符号缺失」——均不覆盖
  OHOS/musl 无 dlinfo(RTLD_DI_LINKMAP) 时的等价枚举替代与本条目新增的可验证
  .dynsym 边界知识
- 本轮新增部分：dl_iterate_phdr + PT_DYNAMIC 解析 + dlsym 过滤的完整替代路径；
  DT_HASH nchain / GNU hash bucket 链遍历求最大索引的可验证条目数边界；bloom
  元素 ElfW(Xword) 8 字节宽度陷阱；无哈希表时跳过（可证明安全）
- reuse_existing: false（两次四范围查重 + 七轴均无完整重复条目可复用）
- new_draft: true（本 .md/.kv 同 stem 配对，仅位于 knowledge/drafts/）
- path_a_no_knowledge: false（本轮修复含真实可复用知识，非普通配方调整）

## 适用边界

- 适用于所有依赖 dlinfo 枚举符号的 C/C++ 库在 OHOS/musl 平台的适配
- d_ptr 相对基址语义（+dlpi_addr）对 dl_iterate_phdr 路径通用
- .dynsym 条目数边界：DT_HASH nchain 优先；GNU hash 按 bucket 链求最大索引；
  无哈希表时不猜测、跳过——三者均为可验证/可证明安全处理
- 若目标只是链接期依赖 libdl（-ldl），应查 E013；本条目专指 dlinfo API 缺失
- 反例：glibc 平台（有 dlinfo）不命中文案；不做符号枚举、仅单符号 dlsym 的库不适用

## 验证与恢复条件

- 验证命令（R02 实测）：上游 gtest C++17 全量 17/17（日志/哈希见上）、OHOS 专项
  7/7（3962 符号、HiLogPrint rc=72）、conan create 1/1、W3 本地 CI 100%（1/1）
- 恢复条件：若目标平台回归 glibc（提供 dlinfo），恢复 `#if defined(__GLIBC__)`
  原路径即可；若 OHOS 新版本 libc 补齐 dlinfo，可移除 #else 分支后复跑上述验证
