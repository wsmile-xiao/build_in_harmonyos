# gamepad-5.15.2-upstream-getter-copy-paste-assert-as-shipped

## 症状

qt5-qtgamepad 5.15.2 消费者测试（test_package）编写 QGamepadKeyNavigation 键映射
断言时，若按构造函数插入的映射（R 键 → Key_Forward）或按文档语义断言：

```cpp
CHECK(kn.buttonR1Key() == Qt::Key_Forward);   // 必然失败
```

实跑失败——getter 实际返回 Key_Back。

## 根因

上游 copy-paste bug：`qgamepadkeynavigation.cpp` 的构造函数为 R 键插入
`Key_Forward` 映射，但 getter `buttonR1Key()`/`buttonR2Key()` 实际读取的是
**ButtonL2** 映射（`buttonR3Key()` 读 ButtonL3），因此三个 getter 全部返回
`Key_Back` 而非 `Key_Forward`。构造函数意图与 getter 行为分裂——**getter 是下游
消费者真正调用的 shipped API 面**。

## 方案：断言对齐（assert-as-shipped）

1. 先读 getter 源码确认每个 accessor 实际读的映射表项；
2. 消费者测试按源码实况断言，就地注释说明上游 bug 与判断依据：

```cpp
// Upstream copy-paste bug (asserted as-is, real behaviour):
// buttonR1Key()/buttonR2Key() read the ButtonL2 mapping and
// buttonR3Key() reads ButtonL3 (qgamepadkeynavigation.cpp getters),
// so all three return Key_Back, not the Key_Forward the ctor
// inserts for the R-buttons. Do not "fix" the expectation to match
// the ctor — the getter source is the shipped API surface.
CHECK(kn.buttonR1Key() == Qt::Key_Back);
CHECK(kn.buttonL2Key() == Qt::Key_Back);
CHECK(kn.buttonR2Key() == Qt::Key_Back);
```

3. 不修改上游源码（路径 A 不扩权为上游 bugfix）；
4. 注释明确 "Do not fix the expectation to match the ctor"——防止后人把断言
   "修正"回构造函数意图导致假失败。

## 回退

若团队决策必须修上游 bug：走独立 patch（patches_applied 显式登记）并在 PR 正文
与测试注释中双向说明，断言按修复后期望值写；该 PR 升级为行为修正类变更。

## 验证（PR #14870）

消费者 test_package 58/58 断言 PASS（含上述三处 getter 如实断言）。

## 推广价值

一切"上游代码有 bug 但适配不扩权修"的场景：消费者测试断言以 shipped 源码行为
为准 + 注释留痕，是"如实记录"与"防止后人误改"的标准做法。

## 关系

- companion: qtgamepad-5.15.2-qmake-prefix-mirror-4pass-sanitize（同 PR 主素材）
- reference: PR #14870 `archives/q/qt5-qtgamepad/5.15.2/test_package/test.cpp`
