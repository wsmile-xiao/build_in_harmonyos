# probalign 1.4 — 框架 L1e 的 conan test 缺 `-pr:b`，交叉早退护栏使真测试被判成假测试（draft）

> 层次定位：**这是 harness（CI 脚本调用参数）层的机制，不是某个包的开发技巧。**
> 一句话：`build_and_test.sh` 的 L1e 重跑 `conan test` 时只传 `-pr`（host profile）不传 `-pr:b`，
> build profile 因此回落到 CONAN_HOME 的 `default`（`os=Linux`），`test()` 里的
> `can_run(self)` / `cross_building(self)` 早退护栏必然命中，测试体被静默 `return`，
> 而 L1e 只看退出码——于是**一个真测试会在 L1e 里被跳过并被判为假测试，一个假测试反而能过 L1e**。

## 症状

同一份配方、同一个 `test_package`，本地 W3 模拟（`reports/w3-local-ci.log` 口径）里出现自相矛盾的组合：

```text
[ok] L1a: test_package was executed by conan create            # 测试确实跑了
[ok] L1b: Test execution evidence found in log                 # 日志里确实有执行证据
PASS: probalign packaged consumer test (29/29 assertions)      # conan create 内 29/29 实跑
...
[step] L1e: Destructive negative test (R34)...
        [sabotage] bin/ moved away
[fail] L1e: test passed WITHOUT package artifacts — fake test detected (R34)
L1_RESULT=fail: negative test: test does not depend on package
```

即：L1a/L1b 说"测试真跑了"，L1e 说"测试不依赖被测包 = 假测试"。两条不可能同时为真。

## 根因

`ci/conan/build_and_test.sh` 里两处 conan 调用的 profile 参数**不对称**（行号为本窗 `grep -n` 实测，非转录）：

| 位置 | 实测行号 | profile 参数 | 后果 |
|---|---|---|---|
| `conan create` 的参数组装 | **316 / 318** | `-pr:h="$PROFILE_FILE" -pr:b="$PROFILE_FILE"` | host 与 build 同一份 OHOS profile ⇒ 非交叉 ⇒ `can_run()` 为真 ⇒ `test()` 实跑 |
| L1e 的 `conan test` 重跑 | **1646-1647** | 只有 `-pr "$PROFILE_FILE"`，**无 `-pr:b`** | build profile 回落 ⇒ 被判交叉 ⇒ `can_run()` 为假 ⇒ 护栏 `return` |

- `PROFILE_FILE` 定义在第 37 行：`PROFILE_FILE="$REPO_ROOT/ci/conan/profiles/$PROFILE"`。
- 回落目标是 CONAN_HOME 的 `profiles/default`，本任务实测内容含 `os=Linux`、`compiler.libcxx=libstdc++11`
  （路径 `/storage/Users/currentUser/tmp/ch/home-z33-probalign/profiles/default`）。
- host=OHOS × build=Linux ⇒ conan 判为交叉构建 ⇒ `cross_building(self)` 真 / `can_run(self)` 假。

两个放大杀伤的细节：

1. **L1e 的判据恰好是退出码**——第 1650 行的 `[fail]` 分支条件就是 `conan test` 返回 0。护栏 `return` 产生退出码 0，于是"跳过"被读成"测试通过但不依赖包"。
2. **该调用把输出整个丢掉**——`>/dev/null 2>&1`（第 1647 行）。护栏自己打印的 `... consumer test skipped: target cannot run here` 连日志都进不去，所以跳过在 CI 侧**完全不可见**。
3. L1e 的 `else` 分支（第 1656 行 `[ok]`）与 `if` 分支同样只看退出码，因此**一个真正的假测试若也走 `return`，同样拿到 0 ⇒ 落到 `[ok]`**。这正是 R34 想拦的东西被 R34 自己放行。

## 最小复现

两条命令**只差一个 `-pr:b`**，同一 recipe、同一 `test_package`、同一 HEAD（`c8e7bed`）。工作树根 = 仓库根，CONAN_HOME 指向任务私有 home。

```bash
# A：L1e 的命令形状（无 -pr:b）
conan test archives/p/probalign/1.4/test_package "probalign/1.4@ohpcd/stable" \
    -pr ci/conan/profiles/ohos-aarch64 --build=missing

# B：补上 build profile
conan test archives/p/probalign/1.4/test_package "probalign/1.4@ohpcd/stable" \
    -pr ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64 --build=missing
```

实测差异（本窗在 HEAD `c8e7bed` 复跑，两条各一次）：

| 输出位置 | A（无 `-pr:b`） | B（有 `-pr:b`） |
|---|---|---|
| 第 22 行 | `Profile build:` | `Profile build:` |
| **第 30 行** | **`os=Linux`**（回落 default） | **`os=OHOS`** |
| 测试体 | 护栏命中 ⇒ `return`（首稿见 `conan-test-probe.log:63` 的 `skipped: target cannot run here`） | 实跑 ⇒ `PASS: probalign packaged consumer test (29/29 assertions)`（`conan-test-with-bprofile.log:100`） |
| 退出码 | 0 | 0 |

**通用自检判据**：任何 `conan test` 的输出头部都有 `Profile build:` 段，看其中 `os=` 是不是 `OHOS` 即可判定这一步有没有把 build profile 带对；不需要读脚本。

破坏性反向自证（护栏已删之后，证明测试真的依赖被测包）：搬走包缓存里的 `bin/` 再跑 A 命令 ⇒
`l1e-negative.log:64` 报 `FAIL: probalign is missing from .../home-z33-probalign/p/b/probaec72c4116ce71/p/bin`，
同次运行 conan 抛 `ConanException: Error 1 while executing ...`，即非零退出；产物随后原样移回。
（注：驱动脚本回显的 `NEGATIVE_RC=1` 只进了终端 stdout，未落盘，故此处以日志内的 `FAIL` + `Error 1` 为准。）

## 已试过的失败方案

1. **照抄仓内先例写护栏**——首稿 `test()` 开头放 `if not can_run(self): return`。该写法取自**已合并**的
   `archives/c/cronutils/1.1/test_package/conanfile.py`（其 `test()` 第 23-26 行即
   `if not can_run(self):` → 打印 skipped → `return`）。结果就是上面的症状：round2 本地 W3 模拟 L1e 判 `fake test`
   （`round2-fail-w3-local-ci.log` 第 295 / 296 / 297 / 303 行）。
2. **保留护栏、但把"为什么跳过"打印出来**——以为有可解释的跳过就行。失败：L1e 用 `>/dev/null 2>&1`
   丢弃全部输出（第 1647 行），提示进不了日志；且判据是退出码，`return` 就是 0，照旧判 `fake test`。
   这条不是推测——首稿的护栏本来就带 `self.output.info(...)` 打印，仍然被判假。

（未尝试、也**不建议**的做法：把 CONAN_HOME 的 `profiles/default` 改成 `os=OHOS` 来"喂平"判定。
那是构建机的全局状态、不在任何包的 PR 范围内，且会顺带改变其它步骤的交叉判定，属越界改动。）

## 最终方案

分层，两条都在本窗验过：

- **根修（框架层，需单开 PR）**：把第 1646-1647 行的 L1e 调用与第 316/318 行的 `conan create` 对齐，补
  `-pr:b "$PROFILE_FILE"`。建议同批把 `>/dev/null 2>&1` 改成留档——否则"测试被跳过"与"测试确实不依赖包"
  在日志里无法区分。**框架改动必须单独 PR，不得夹进配方 PR**（本轮未改，交主代理定夺）。
- **包内自保（本包采用，提交 `a281710157`）**：`test()` 不放交叉/可运行性早退护栏。本包
  `package_type="application"`，唯一可消费产物就是 `bin/probalign`——"跑不了"对 CLI 包是**失败**而不是**跳过**。
  现行代码在 `archives/p/probalign/1.4/test_package/conanfile.py` 第 26-35 行留了注释说明这个理由。
  修后 round3：`[ok] L1e: Negative test confirmed — test genuinely depends on probalign`
  （`round3-w3-local-ci.log` 第 290 / 292 / 297 行），且消费者断言 29/29。
- **纪律推论（对本层机制的直接应对）**：**不得把"L1e 变绿"当作"测试真跑过"的证据**。
  L1e 绿只说明"产物搬走之后 `conan test` 退出码非 0"，而 L1e 红也可能只是护栏跳过了。
  验收要自己做一次破坏性复现（搬走 `bin/` 必须 FAIL、放回必须 PASS），两头都测。

## 适用边界

- **命中条件**（三者同时成立才会中招）：① 配方 `test()` 里有交叉/可运行性早退护栏
  （`can_run(self)`、`cross_building(self)` 及其"打印后 return"变体）；② 走的是框架 L1e 这一步；
  ③ CONAN_HOME 的 `profiles/default` 的 `os` 与 host profile 不同。
- **不受影响**：纯库包中测试体本就不执行产物的情形（走 `L2_RESULT=skip: no bin/` 一类路径）；
  以及不写护栏的 CLI 包——删掉护栏后，连 L1e 的命令形状（无 `-pr:b`）也会实跑 29/29
  （本窗 `confirm-A-noprb-HEADc8e7bed.log:93`）。
- **跨包一般性**：护栏写法不是本包独创。已合并的 `archives/c/cronutils/1.1/test_package/conanfile.py`
  就是这个写法（其归档提交于 2026-09-13，而 L1e 早在 2026-07-06 的 `2ece696d39` 就已引入 ⇒ 该写法是在
  L1e 存在的前提下被合入的，说明当时 L1e 未对它报错，原因见下条）；同机另一在途包 ruli 0.36 的
  `test_package/conanfile.py` 由另一代理**独立**写成 `if cross_building(self): return`（本窗只读观察，
  不作为本条目成立依据）。⇒ 这是被当作通用范式在复制的写法，暴露面是真实的。
- **本窗否证过强结论**：cronutils 带着护栏仍然合入了，说明它那一轮 L1e 没有误判它——可能的解释包括
  L1e 走了第 1637 行的 `[skip] L1e: No standard artifact dirs found to sabotage` 分支、
  或其 CI 侧 CONAN_HOME 的 `default` 与本机不同。**因此本条目只对 probalign 1.4 断言"CI/L1e 中实际发生"**
  （那有 round2/round3 两轮 A/B 判决为证），对其它包只断言"写法命中三条件、属潜在暴露"。

## 与 E374 的关系（层次差，非重复）

`knowledge/graph/E374.kv` 的 `forbid_1_pattern` 含 `can_run\(self\).*return.*pass`，明文禁这类护栏，
且 `forbid_1_consequence`（"CI appears green without proving either valid artifacts or the intended target behavior"）
与本包后果一致。**但两条不在同一层**：

- **E374 = 配方作者层的行为禁令**。它的 `root_cause` 前提写得很清楚——"A **same-OS** worker can therefore
  compile and link a real consumer while being unable to safely execute that consumer"，
  `affected_scope` 也限定在 "on workers where **build and host settings match**"，
  关心的是**签名工具链缺失**时如何如实上报 `NOT_RUN`。它假设 build/host 一致。
- **本条 = 框架 L1e 调用参数不对称导致验证通道失真**。build/host 之所以不一致，不是工人环境，
  而是 `conan create` 传了 `-pr:b` 而 L1e 没传。此时 E374 的前提（same-OS）根本不成立，
  它给的那些"如实上报 NOT_RUN"的处置也无从谈起。

二者是**禁令与成因**的关系：E374 说"别这么写"，本条解释"为什么这么写的后果无法被 L1e 自行发现"——
因为 L1e 的判据（退出码）与它要防的东西（跳过冒充通过）之间，正好被自己少传的那个 `-pr:b` 打通了。
命中 E374 的配方作者若只按 E374 整改（例如改报 `NOT_RUN`），在 L1e 这一层依然拿不到正确判决。
交叉引用已写入 `.kv` 的 `similar_to: E374`。

## 证据索引

设备证据目录：`/storage/Users/currentUser/tmp/uc2/z33-probalign/`（B 机）。仓库内路径相对仓库根。

| 事实 | 位置 |
|---|---|
| L1e 只传 `-pr`、丢弃输出 | `ci/conan/build_and_test.sh:1646-1647` |
| `conan create` 同传 `-pr:h` 与 `-pr:b` | `ci/conan/build_and_test.sh:316`、`:318` |
| `PROFILE_FILE` 定义 | `ci/conan/build_and_test.sh:37` |
| L1e `[fail]`（退出码 0 ⇒ 判假） | `ci/conan/build_and_test.sh:1650` |
| L1e `[ok]`（退出码非 0 ⇒ 判真） | `ci/conan/build_and_test.sh:1656` |
| L1e 无产物可破坏时 skip | `ci/conan/build_and_test.sh:1637` |
| CONAN_HOME `default` 为 `os=Linux` | `~/tmp/ch/home-z33-probalign/profiles/default` |
| 无 `-pr:b` ⇒ build profile `os=Linux` | `conan-test-probe.log:22,30`；本窗复跑 `confirm-A-noprb-HEADc8e7bed.log:22,30` |
| 护栏命中 ⇒ 跳过 | `conan-test-probe.log:63` |
| 有 `-pr:b` ⇒ `os=OHOS` + 29/29 | `conan-test-with-bprofile.log:22,30,100`；本窗复跑 `confirm-B-withprb-HEADc8e7bed.log:22,30,100` |
| 带护栏时 L1e 判假（失败轮） | `round2-fail-w3-local-ci.log:295,296,297,303` |
| 删护栏后 L1e 判真 | `round3-w3-local-ci.log:290,292,297` |
| `conan create` 内 29/29 | `archives/p/probalign/1.4/reports/conan-create.log:122` |
| L1a/L1b 与 L1e 同绿 | `archives/p/probalign/1.4/reports/w3-local-ci.log:280,284,285,290,292` |
| 破坏性复现 FAIL（非零退出） | `l1e-negative.log:64` |
| 护栏写法先例（已合并） | `archives/c/cronutils/1.1/test_package/conanfile.py:23-26` |
| L1e 引入时间 | `2ece696d39`（2026-07-06） |
| cronutils 归档时间 | `6b0ad13860`（2026-09-13） |
| 本包最终 `test()`（无护栏 + 理由注释） | `archives/p/probalign/1.4/test_package/conanfile.py:26-41` |
