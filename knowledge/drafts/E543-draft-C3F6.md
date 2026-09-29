# E543: rotate_left(n==0) 移位越宽 UB — 测试 -O0 全过而 -O2 全错（digestpp LSH 案例）

## 错误特征
```
LSH256/256 error: expected f8025b61eb10d80a7f03ccfb906222a0645bb175fdeee9595f223936edbf7070, actual 15de4d72aa9a7589e089c83794a0b0cb2744f102aebe8b33bf0bfb638e043249
Self-test completed with 4 errors.
lsh256/224: 7/7 FAILED
lsh512/512: 7/7 FAILED
```
同一源码 `-O0` 下 `Self-test completed with 0 errors.`、`test_vectors` 95/95 全过；
`-O2`（Release）下全部 LSH 套件确定性失败，其余算法（sha/blake/skein 等）不受影响。

## 触发条件
- 构建系统: cmake（header-only 或常规 C/C++ 库均可命中）
- 阶段: 编译 + 运行测试（Release/-O2 构建）
- 前置条件:
  - 代码使用手写循环左移 `rotate_left(x,n) = (x << n) | (x >> (W-n))`
  - 存在 n==0 的调用点（如 LSH 旋转常量表 G256={0,8,16,...}、G512={0,16,32,...}）

## 根因分析
`n==0` 时表达式退化为 `(x<<0) | (x>>W)`，其中 `x >> W` 是“移位量 ≥ 字宽”的**未定义行为**（UB）。
- clang -O0 下生成真实硬件移位指令，ARM/x86 移位器对移位量按字宽取模（32&31=0），
  恰好得到正确结果 → “-O0 全过”。
- clang -O2 下 LLVM 把 `lshr x, W` 视为 poison 并确定性折叠，整个结果被污染
  （不同消息出现相同错误后缀，是 poison 传播特征）→ “-O2 全错、确定性”。
辅助根因：`lsh_provider::init()` 在 `memset(msgexp,0)` 之前调用首次
`transform(msg,1)`，而 `msgexpand()` 从不写 `msgexp` 第 1 行 → 首次 transform
读取未初始化成员（另一处 UB）。
上游 CI 默认不设 CMAKE_BUILD_TYPE（无优化）故未暴露；上游 master（2026-02-14）
与受影响 commit 完全一致，bug 在上游仍存在。

## 推荐方案
**方法**: rotate-zero-guard-and-init-scratch-vs-transform-order

**说明**:
1. `rotate_left` 32/64 位两处改为 `return n ? (x << n) | (x >> (W - n)) : x;`
   —— 消除移位越宽 UB，n==0 恒等，其他调用点语义不变。
2. `lsh_provider::init()` 把 `memset(t)`、`memset(msgexp)` 移到首次 `transform(msg,1)`
   之前，消除未初始化读取。
3. 无平台宏，纯 bugfix，可回馈上游。

## 验证/命令
```
clang++ -std=c++17 -O2 -I<prefix>/include test/test.cc -o test && ./test        # Self-test completed with 0 errors. (exit 0)
clang++ -std=c++17 -O2 -I<prefix>/include test/test_vectors.cc -o tv && ./tv    # 95/95 套件 OK, 0 FAILED (exit 0)
conan create . -pr:h=ci/conan/profiles/ohos-aarch64                              # G2 PASS
```
修复后 -O0/-O2 输出与官方向量一致（sha256sum 对照 testvectors/*.txt）。

## 适用范围 / 边界 / 反例
- 适用：所有用 `(x<<n)|(x>>(W-n))` 手写旋转、但旋转常量表含 0 的 C/C++ 库
  （ARX 类密码/哈希算法尤甚）；也适用于“测试 -O0 全过、-O2 全错”的通用排查路径。
- 边界：若 rotate_left 从未以 0 调用则不会命中；-O0 硬件取模掩盖 UB 不可依赖。
- 反例：上游测试在无优化构建下全过**不能**作为“无 bug”的反证（E543 正是该反证失效的案例）。

## 七轴查重与关系
- exact/causal_duplicate: false；trigger/solution_overlap: false；组合/边界/测试迁移新颖性: true
- similar_to: 无（E408 为 Perl AppConfig，仅关键词噪声）
- source_pr: 无（本轮适配产生，尚未回馈上游）

*来源: digestpp 1.0.0 适配（task digestpp-1.0.0-r01-pc4-7-20260928T013018Z）*