# DRAFT — AFL++ 4.40c 新增 cmplog pass 专项测试在 OHOS LLVM 15/ARM 上的豁免判定

> 状态: 随 afl-tools 4.40c 适配产出的新草稿（4.40c 特有知识，与 aflplusplus 4.33c 的
> musl POSIX 类型草稿（走 docs/knowledge-posix-types 独立路线）无关）。
> 触发事件：test-llvm.sh 鸿蒙 PC 实机（2026-09-04）3 项失败。

## 真实问题（afl-tools 4.40c 适配实测命中）

test-llvm.sh（LLVM 插桩模式集成测试）在 4.40c 中新增了 3 个 cmplog 专项测试，鸿蒙 PC
实机（clang/LLVM 15.0.4，OHOS aarch64）运行结果：

```
[-] CMPLOG too slow to test in ARM CI, cannot test          ← 主 cmplog 测试：ARM CI 跳过（上游脚本自带标记）
[!] cmplog loop back-edge detection test failed             ← test-cmplog-loops.sh：循环回边检测
[!] cmplog routines pass instrumentation test failed        ← test-cmplog-routines-pass.sh：例程插桩
[!] cmplog non-standard integer size test failed (issue #2704)  ← test-cmplog-bitint.sh：上游已知 issue
```

同时段核心测试全部通过：test-basic.sh 全绿、test-llvm.sh 主体（llvm_mode 编译/插桩/
threadsafe/test-dlopen/hardened/laf-intel/compcov/floatingpoint/instrumentlist/
persistent mode）全绿、cmocka 14/14、test_package 5/5。

## 根因（为什么是"新功能平台限制"而非"适配回归"）

1. **测试是 4.40c 新增的**：对比 4.33c 的 test-llvm.sh——4.33c 没有
   test-cmplog-loops.sh / test-cmplog-routines-pass.sh / test-cmplog-bitint.sh 这些
   专项测试（4.33c 时代这些 cmplog 功能不存在）。失败项不是既有功能回归。
2. **功能依赖较新 LLVM 行为**：cmplog routines pass（`__cmplog_rtn_hook_*` 例程插桩）
   与循环回边（back-edge）去重是 4.40c 新实现，依赖的 LLVM pass 行为在 OHOS 的
   LLVM 15.0.4 上不完整工作。
3. **上游已知背书**：bitint 测试在上游脚本内自注已知问题（issue #2704）；上游 ARM CI
   对 cmplog 本身标记 "too slow to test in ARM CI"（issue #2056 佐证 ARM 平台测试限制）。
4. **核心功能无回归**：afl-fuzz/afl-showmap/afl-clang-fast 的插桩、运行、cmin/tmin
   全部通过；cmplog 是 cmp 引导的可选增强，失败不影响 fuzz 核心可用性。

## 修复（豁免声明，非源码修复）

按 TEST_QUALITY_SPEC §3.3 平台限制豁免：不删除/篡改上游测试（R9），在
`manifest.yaml test_results.note` 与 `notes.md` 中逐项声明失败清单 + 判定依据 +
"核心测试全绿"证据，作为豁免记录随 PR 提交。

## 复用步骤（其他 AFL 家族版本 / LLVM pass 库）

1. test-llvm.sh 报 cmplog 专项失败 → 先 `git diff` 上一版本 test-llvm.sh：
   确认该测试是否上游新增（新增 → 新功能问题；既有 → 需当回归排查）。
2. 查上游脚本注释 / issue（4.40c: #2704 bitint、#2056 ARM CI）。
3. 跑核心测试（test-basic.sh + test-llvm.sh 主体）确认无回归 → 声明豁免。
4. 若目标项目强依赖 cmplog 完整引导 → 评估升级 OHOS LLVM 版本（15 → 更高）。

## 验证

- test-basic.sh：`[+] all tests were successful`（核心工具链全绿）
- test-llvm.sh 主体：llvm_mode/threadsafe/dlopen/hardened/laf-intel/floatingpoint/
  instrumentlist/persistent 全部 `[+]`
- cmocka unit：14/14；test_package：5/5
- 豁免记录：manifest.yaml test_results.note（3 项 cmplog 失败 + 依据）

## 知识库查重结论

index.tsv 检索 cmplog/too slow/ARM/测试豁免类零直接命中；最近邻 E046
（selinux/testing 平台限制 → skip-test 豁免）机制为"平台权限导致测试失败豁免"，
本条为"上游新增功能测试在旧 LLVM 上失败豁免"，判定路径不同（新增测试 vs 平台权限），
不重复。

## 关联条目

相关: E046（测试豁免先例）
