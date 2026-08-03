# LLVM 插件入口验证报告 — enzyme 0.0.284

> **报告目的**: 证明 test_package 对 enzyme 的 LLVM 插件入口（llvmGetPassPluginInfo）进行了实质验证，满足 R34（test 必须实质依赖被测包，禁止 false pass）。
> **生成日期**: 2026-07-24
> **知识库**: E216-draft-enzyme-llvm-sdk-lit-ohos（路径 B 10 分候选 + 路径 C 专项终审候选）

## 验证目标

enzyme 是 LLVM AutoDiff pass/plugin 库。其标准插件入口为 `llvmGetPassPluginInfo`（LLVM pass plugin 标准 API），符号位于 `libLLVMEnzyme-15.so`。

## 验证策略：nm 符号存在性检查

由于 OHOS SDK LLVM 15 的单体 `libLLVM-15.so` 未导出数百个 LLVM C++ API 符号（E216-draft 缺口 4），`dlopen("libLLVMEnzyme-15.so")` 无法通过 relocation——runtime dlopen/dlsym/实际调用不可行。因此验证采用 **nm 静态符号存在性检查**（不触发 relocation）：

### 流程

1. **conanfile.py test()**: 在 Conan 包缓存中定位 `libLLVMEnzyme-15.so` 的实际路径
2. **test_enzyme 执行**: conanfile.py 以 `ENZYME_PLUGIN_LIB` 环境变量传入路径，调用 `self.run(test_exe, env=["conanrun", "ENZYME_PLUGIN_LIB=..."])`
3. **test.c**: 从 `ENZYME_PLUGIN_LIB` 读取路径，执行 `nm -D <path> | grep -q llvmGetPassPluginInfo`
4. **失败处理**: nm 找不到文件或 grep 不命中 → `return 1`（R34：无 false pass）

### L1e 反向验证（R34 兜底）

`build_and_test.sh` 破坏性测试：`lib/` 目录被移走后，nm 找不到 `libLLVMEnzyme-15.so` → `test_enzyme` 返回 1 → `conan test` 失败 → L1e 判定"真测试"（依赖被测包）。

## R34 合规性

| R34 要求 | 实现 | 合规 |
|---------|------|------|
| test 必须实质依赖被测包 | test_enzyme 通过 CONAN_PACKAGE_CACHE 查找被测包产物，传入 ENZYME_PLUGIN_LIB 路径 | ✅ |
| 禁止只打印字符串的空壳测试 | test.c 执行 nm 命令并检查匹配结果，失败 return 1 | ✅ |
| CI L1e 破性反向验证兜底 | sabotage 移走 lib/ → nm 找不到 .so → return 1 → genuine dependency confirmed | ✅ |

## test_package 统计

- **test_package 测试数**: 1（test_enzyme）
- **实质验证数**: 1（nm -D 符号存在性检查，未触发 relocation）
- **断言数**: 3（ENZYME_PLUGIN_LIB 非空 / nm 可执行返回 0 / grep llvmGetPassPluginInfo 命中）

## 已知限制

- runtime dlopen/dlsym/实际调用因 OHOS SDK LLVM 单体 libLLVM-15.so C++ API 符号导出缺口未作为通过条件。此为 OHOS SDK LLVM 工具链缺口（E216-draft 缺口 4），**路径 C 候选，需评审委员会专项终审，最终以官方审核为准**。

---

*evidence: plugin-entry-validation.md · 2026-07-24 · PR !2786 · E216 draft · R34 compliant*