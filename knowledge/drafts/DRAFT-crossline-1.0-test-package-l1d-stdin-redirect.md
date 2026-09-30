# DRAFT：test_package 消费者喂 stdin 时禁用 echo/print 管道（CI L1d 正则误判），改用输入文件 + stdin 重定向

> Status: **Draft**（待审核 promote）| severity: `2` | category: `conan, testing, ohos, ci-gate, packaging` | Updated: 2026-09-28
> 对应: `knowledge/drafts/DRAFT-crossline-1.0-test-package-l1d-stdin-redirect.kv`
> 触发事件: crossline 1.0（纯 C readline 替代库）HarmonyOS PC 适配

---

**匹配关键词**：test_package, L1d, fake test, self.run, echo, print, pipe, stdin, redirect, readline, consumer, build_and_test.sh

## 错误签名（error_signature）

```text
L1_RESULT=fail: fake test detected
L1d: test() method appears to be a fake test (echo/print/true only)
self.run.*echo.*|.*consumer
```

## 错误摘录（error_excerpt，crossline 1.0 实测）

```text
❌     L1_RESULT=fail: fake test detected
❌     [fail] crossline/1.0 — L1 official test failed
```

W3 本地 CI（ci/conan/build_and_test.sh）的 L1d 门禁用
`grep -qE "self\.run.*(echo|print|true)"` 判定 test() 为假测试并拦截。
当 test_package 的 test() 写成 `self.run("echo 'hello' | ./consumer")`
给消费者喂 stdin 时（readline 类库消费者在非 TTY 路径用 fgets 读一行，
裸跑 stdin=EOF 直接返回 NULL），命中该正则 → 真实测试被误判为
"fake test detected"，finish 阻塞。

## 根因（root_cause）

1. 消费者二进制（readline 替代库 / 交互式 CLI）需要从 stdin 读取输入；
   非 TTY 路径下 `crossline_readline` 走 `fgets(buf, size, stdin)`，
   stdin 为 EOF 时返回 NULL，测试失败。
2. 开发者直觉用 `echo '...' | ./consumer` 管道喂 stdin，但命令串包含
   `self.run.*echo`，触发 CI L1d 假测试正则（R34 空壳测试前置拦截），
   即使测试真实调用被测库 API 也被判 fake test。

## 推荐方案（rec_approach: `input-file-stdin-redirect`）

test() 内先把需要喂入 stdin 的行写入构建目录下的输入文件，再以 `<`
重定向执行消费者二进制；命令串中不出现 echo/print/true：

```python
def test(self):
    if not cross_building(self):
        consumer = os.path.join(self.cpp.build.bindir, "crossline_consumer")
        input_file = os.path.join(self.build_folder, "stdin.input")
        with open(input_file, "w", encoding="utf-8") as f:
            f.write("hello-crossline\n")
        self.run(f"{consumer} < {input_file}", env="conanrun")
```

- 避开 L1d 正则（无 echo/print/true）
- 仍是真实执行消费者并调用被测库公开 API（满足 R34）
- crossline 1.0 实测：修复后 W3 `L1_RESULT=pass: test_package executed`，100% (1/1)

## 验证（verification_cmd）

```bash
# 修复前（echo 管道）→ W3 报 fake test detected
python3 scripts/ohc-run.py finish crossline 1.0 built
# 修复后（输入文件重定向）→ W3 pass
python3 scripts/ohc-run.py finish crossline 1.0 built
# w3-local-ci.log: L0 pass / L1 pass / L5 pass, Pass rate: 100.0% (1/1)
```

## 查重与关系

| 轴 | 结论 | 说明 |
|----|------|------|
| exact_duplicate | false | 无既有条目覆盖「echo 管道触发 L1d 正则误判 + 输入文件重定向」 |
| causal_duplicate | false | E472 根因是 ELF 签名/SDL dummy，非 stdin 喂入写法 |
| trigger_overlap | 部分 | E472 亦涉及 test() 需真实 self.run，但触发面是签名/SDL，非 L1d echo 正则 |
| solution_overlap | 无 | E472 方案=签 ELF+dummy env；本条=输入文件重定向 |
| combination_novelty | true | stdin 消费 + L1d 正则规避的新组合 |
| boundary_novelty | true | 适用于 readline 类/交互 CLI 的 test_package；纯库不受影响 |
| test_migration_novelty | true | 其他 readline/交互库 test_package 可复用 |

关系字段：`similar_to=E472`，`caused_by=none`，`prerequisite_of=none`，`conflicts_with=none`。

适用边界/反例：仅消费者需 stdin 输入的库受影响；若 CI L1d 未来改为结构性检查，
本条方案仍是无害且更清晰的写法。

---

*本文件由 `knowledge/drafts/DRAFT-crossline-1.0-test-package-l1d-stdin-redirect.kv` 字段派生生成（补齐 kv↔md 配套）；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*
