# E546（草稿）跨 DSO 各自实例化同一模板特化 → 多个 WEAK typeinfo → dynamic_cast 恒失败（SIGSEGV）

- **现象**：共享构建（主库 + dlopen 插件）下，forcefield/descriptor 相关 ctest 用例 SIGSEGV；单步可观察到 `dynamic_cast<OBPairFloatingPoint*>` 返回 null 后解引用。
- **根因**：`OBPairTemplate<int/double/bool>` 在各 DSO 的 TU 中隐式实例化，链接器允许每个 DSO 各留一份 WEAK typeinfo/vtable。aarch64 采用 Itanium ABI 的**唯一 typeinfo 语义**（`typeinfo` 的 `operator==` 只比较指针），跨 DSO 的两个"相同" typeinfo 指针不等 → `dynamic_cast` 恒判失败。
- **解法**（可移植，无平台宏）：`generic.h` 对三个常用特化加 `extern template` 声明；`generic.cpp` 在 libopenbabel 内单点显式实例化。全进程每个特化只剩一个强符号 typeinfo/vtable，跨 DSO dynamic_cast 恢复。
- **验证**：`nm` 确认 3 个特化各 1 个强符号 typeinfo；上游 ctest forcefield/descriptor 组无段错误（348/348 全过）。
- **关联**：E545（同形态多 DSO 问题，注册表面）。
- **来源**：openbabel 3.2.1 OHOS aarch64 适配，PR #14369。
