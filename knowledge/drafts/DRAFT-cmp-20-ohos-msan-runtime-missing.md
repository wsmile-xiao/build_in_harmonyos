# DRAFT-cmp-20-ohos-msan-runtime-missing：OHOS SDK clang 15 不随附 MSan 运行时

## 现象

HarmonyOS PC 适配 cmp 20 时，上游 Makefile 的 MSan 测试变体（cmpmemtest）编译通过，
链接失败：

```text
ld.lld: error: cannot open /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/
  ohos/native/llvm/lib/clang/15.0.4/lib/aarch64-linux-ohos/libclang_rt.msan.a:
  No such file or directory
clang-15: error: linker command failed with exit code 1
```

## 根因

OHOS SDK（26.0.0.18）自带的 clang 15 工具链 **lib 目录未包含
libclang_rt.msan.a**（MemorySanitizer 运行时）。同一目录下
`libclang_rt.asan.a`、`libclang_rt.ubsan.a` 齐全，因此 ASan/UBSan 变体可用，
仅 MSan 变体不可链接。这是平台工具链能力缺失，不是当前库源码/配方/补丁错误。

## 可复用模式

1. MSan 变体如实记录为**平台工具链限制**：命令、退出码、首错（ld.lld cannot
   open libclang_rt.msan.a）、恢复条件（工具链提供 msan 运行时）。
2. 用同工具链可用的 ASan/UBSan 变体覆盖消毒器验证（cp -f 移植 Makefile 的
   `-fsanitize=undefined` / `-fsanitize=address` 配置并运行）。
3. 台账中明确 MSan 变体是**同一用例集的不同构建配置**，不是独立上游用例缺失，
   不计入全量分母的"未实例化"。

## 验证

```bash
ls /data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib/clang/15.0.4/lib/aarch64-linux-ohos/
# asan/ubsan 运行时存在，msan 缺失（平台侧证据）
```

## 适用范围与反例

- 适用：OHOS PC（clang 15 SDK）上任何声明 `-fsanitize=memory` 测试变体的三方库。
- 反例：使用完整 LLVM 发行版（自带 msan 运行时）的环境可正常运行 MSan，
  不受本限制约束；仅链接不能代替验证。

## 与既有知识的关系

- 相关：knowledge/musl-glibc-developer-impact.md 仅概述 "MSAN 需 musl 适配"，
  未记 SDK 未随附运行时导致的链接失败细节。
- similar_to: E387（llvm lit 测试工具链问题，不同错误面）。
- 无 exact/causal duplicate；solution_overlap 低；boundary_novelty 高
  （明确边界 = 工具链 lib 目录无 msan 运行时）。

## 七轴快查（本候选）

- exact_duplicate: false（无既有条目记录 MSan 链接失败）
- causal_duplicate: false
- trigger_overlap: 低（与 E387 均涉 sanitizer/llvm 测试但触发面不同）
- solution_overlap: 低
- combination_novelty: 高（sanitizer 变体 × OHOS-SDK-clang15 组合）
- boundary_novelty: 高（工具链 lib 目录层面精确定界）
- test_migration_novelty: 中（不改测试，仅如实分类）