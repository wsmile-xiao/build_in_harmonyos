# DRAFT-hippomocks-5.0-cfunc-mock-aarch64-wx — 知识草稿说明

> 与 `knowledge/drafts/DRAFT-hippomocks-5.0-cfunc-mock-aarch64-wx.kv` 配套（同 stem）。
> 路径 B（知识库扩展）草稿，来源 PR：feat/hippomocks-5.0（task hippomocks-5.0-r01-pc7-36-20260928T011831Z）。

## 问题

在 aarch64 / HarmonyOS PC (OHOS) 上编译并运行 hippomocks 5.0：

1. **编译期**：`HippoMocks/hippomocks.h:110` 的
   `extern "C" void __clear_cache(char *beg, char *end);`
   与 clang 内建 `void __clear_cache(void *, void *)` 冲突，报
   `conflicting types for '__clear_cache'`。
2. **运行期**：上游测试二进制在首个 CFUNC 用例 `checkFunctionReplacedAndChecked`
   （`HippoMocksTest/test_cfuncs.cpp`）SIGSEGV（Signal 11）。

## 根因

- `__clear_cache` 是 clang/ARM 的内建函数（签名 `void(void*, void*)`），
  上游用 `char*` 重声明触发 conflicting-types。
- CFUNC 打桩（`Replace` 类，hippomocks.h `#elif defined(SOME_ARM)` 分支）
  只写入 **32 位 ARM 指令**（`rawptr[0]=0xE59FF000` 等），aarch64 上执行即崩溃；
- 且打桩需要把目标函数所在文本页 `mprotect` 为 `PROT_READ|PROT_WRITE|PROT_EXEC`，
  OHOS 内核强制 W^X（Write XOR Execute，与知识条目 E045 mmap RWX 同族），
  实测 `mprotect` 返回 `EINVAL (22)`——文本页不可写，打桩不可行。

## 方案（本补丁）

- `_HIPPOMOCKS__ENABLE_CFUNC_MOCKING_SUPPORT` 的 SOME_ARM 分支增加
  `&& !defined(__aarch64__)`：aarch64 上禁用 CFUNC 打桩。
  上游用该宏门控 CFUNC 测试（`test_cfuncs.cpp` 内
  `// If it's not supported, then don't test it.`），禁用后相关测试自动排除。
- `__clear_cache` 声明 `char*` → `void*`（char* 可隐式转换为 void*，行为不变）。
- 虚拟函数打桩（`MockRepository` / vtable）不依赖文本页改写，完全不受影响。

## 验证

- 上游测试：`./build-ohos/HippoMocksTest/HippoMocksTests` → **75 of 75 successful**（rc=0）；
  `ctest` 100% passed。
- 双口径：源码声明 84（`TEST (...)` 可复制枚举），当前配置实例化 75 并全过；
  9 个未实例化均有明确上游互斥条件（6 个 `_MSC_VER` 专属 stdcall + 3 个 CFUNC/WIN32）。
- conan-verify：G1-G4 + L2/L4/L5 全过；W3 本地 CI 模拟 L0/L1 pass（100%）。
- test_package：消费者用例 + 鸿蒙专项测试均 PASS。

## 适用边界与反例

- 仅 aarch64 受影响：32 位 ARM 保留上游原行为；x86/Apple 分支不受影响。
- 反例：若下游硬性依赖 CFUNC 打桩，OHOS 内核 W^X 为硬限制（E045 同族），无用户态绕过，应改用虚拟函数打桩设计。
- 仅需文本页 mprotect RWX 的自修改代码/打桩类 mock 框架均可参考本方案思路。

## 查重

对照 knowledge/graph/index.tsv（540 条目）与 knowledge/doc/：
- exact_duplicate: false；causal_duplicate: false（E045 为 mmap 分配 RWX 被拒，非已有文本页打桩）；
- trigger_overlap: 部分（仅 mprotect/Invalid argument 关键词与 E045 重叠）；
- solution_overlap: 无；combination_novelty/boundary_novelty/test_migration_novelty: 有。
- similar_to: E045；caused_by: 上游仅实现 32 位 ARM CFUNC 打桩 + OHOS W^X；
- 决定：new_draft（本条目），reuse_existing: false。
