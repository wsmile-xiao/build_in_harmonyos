# E545 — 旧式 config.sub 的 Linux 改写需按 case 首匹配判定可达性

## 错误特征
`machine 'aarch64-unknown-linux' not recognized` 可来自 kernel/OS 切分错误，不等于 CPU 缺失。修正切分后，有些资料要求只要看到 `-linux*)` 就增加第三个 OHOS 空分支；但在同一 case 中，较早白名单可能已先匹配并结束，后续改写不可达。

## 触发条件
- 发布源码内置旧式 config.sub，maybe_os 的 kernel/OS 表尚未接受 linux-ohos。
- OS 白名单和 Linux -> GNU 改写位于同一 shell case，白名单在前、以 `;;` 结束。

## 根因分析
shell case 执行首个匹配分支；`;;` 不会向后续分支落下。libpagemaker 源码的较早 OS 白名单添加 `-linux-ohos*` 后，canonical OS 被保留，尽管文件仍含较晚的 `-linux*) os=...linux-gnu...`。所以不能只按年份或全文出现该分支决定“必须三个 hunk”。

这为 E344 的年份/hunk 数建议提供实证边界；E564 已给出旧解析器双锚点，本条新增独立可复核的控制流选择规则，解释为什么它与“三 hunk”建议不冲突，而不是再列一次双锚点补丁。

## 解决方案

### 推荐方案
1. 核对真实 CPU 表，先分析完整错误机器 token；已有 aarch64 时不要再扩写 CPU 列表。
2. 修 maybe_os 表，使四段输入被分为 machine=aarch64-unknown / os=-linux-ohos。
3. 定位 OS 处理 case，沿分支顺序找首次能匹配该 os 的模式及终止符。若较早白名单已以 `;;` 截住，不需要额外 OHOS 空 case。
4. 如果白名单与 rewrite 是两个独立 case，或前面的分支不截住 OHOS，才需增加 E344 的显式保护。不要据此否定所有第三 hunk。
5. 验证脚本语法、正式补丁 dry-run、canonical 完整输出和 configure build/host 身份，再构建与运行消费者。

### 禁止做法
- 不按“2018 年前”或 grep 到 `-linux*)` 固定增加空分支。
- 不把误切分的 aarch64-unknown-linux 当作新 CPU 名加入白名单。
- 不只看 config.sub RC0；必须核对输出没有变成 linux-gnu-ohos。

## 验证
官方 release SHA-256 `66adacd705a7d19895e08eac46d1e851332adf2e736c566bef1164e7a442519d`，config.sub 的 OS 白名单位于 -linux*) 之前且以 `;;` 结束。正式 `0002-config.sub.patch` 只有 maybe_os 和较早 OS 白名单两个 hunk，没有新增第三空分支。

r1 报 machine aarch64-unknown-linux 不识别；r2 的 `sh config.sub aarch64-unknown-linux-ohos` 输出逐字相同，configure build 与 host 均为 linux-ohos。完整 Conan create RC0、make check RC0（发布包无注册测试程序）、真实 PMD -> SVG 消费者 14 断言通过，日志 SHA-256 `9f8b2165d114fa6f32c6729f519c3927f0547def23a87afbbcb98493202e5eeb`。这是前轮原生证明，不代替正式 finish/比赛 CI。

## 关联条目
- E344：三 hunk 的建议，新增的是首匹配与独立 case 的适用边界，而非否定它的正确使用场景。
- E572：旧 CPU/系统识别；本例 CPU 已有支持，错误 token 来自 OS 切分。
- DRAFT-E564-oldstyle-config-guess-ohos-reanchor：双锚点已知修复，本条解释何时它已阻断后续 GNU rewrite。
- graph/drafts/doc/operations 已查询 machine-linux 拒绝、first-match、whitelist precedence、Linux 改写与 case 首匹配；必须保留已命中的双锚点知识，不声称所有 OHOS 解析问题都为新模式。


## 2026-10-13 CI 反例与修复增量

A large mostly sparse binary sample can be transported as compressed text while preserving its original bytes. Bound decompression to expected_size+1 and require end-of-stream, no unused/trailing input, exact size and SHA256 before writing the consumer fixture.

Do not claim compression as new knowledge. The increment is the validation order that prevents a compact text carrier from changing test semantics or expanding without a bound in a text-only CI patch workflow; never replace the 96256-byte original sample with a smaller synthetic fixture.

验证：新事务 `libpagemaker-ci-repair-w3-20261013-r1` 的12阶段及释放通过；当前官方本地CI子步骤 exit0，原始CI日志 SHA256 `d2cfda0b1ee12575dd553744b1446523666da45827f4d46744e2d13bb4a87b61`。上游声明 0 项及消费者 1 程序口径保持不变；原有整体finish失败/旧标记不改写为成功，比赛worker结果必须绑定新HEAD另查。


## 2026-10-14 CI 反例与修复增量

Autoconf creates config.status scratch directories in two branches with owner-only masks. On HMDFS, changing file modes later or repairing PR transport cannot establish creation-time access. Replace both creation branches with exclusive mkdir under the recipe-private TMPDIR, use umask 022 at creation, restore configure timestamps, and prefix TMPDIR after Conan environment activation. Preserve cleanup and every original test.

Current worker logs provide the independent second-failure boundary after the earlier checkout/fixture repair: successful source retrieval and dependency installation are not proof that configure generated usable config files. Use both-branch source reconciliation, timestamp-preserving production-helper tests and complete native recipe/tests; do not treat a missing-curl predownload warning as the cause when source() already succeeded. This extends the existing evidence/transport topic with a causal validation boundary, not a new generic umask claim.

验证：新事务 `libpagemaker-ci-repair-w3-20261013-r101` 的12阶段及释放通过；当前官方本地CI子步骤 exit0，原始CI日志 SHA256 `1169a21695c87b42adb547dbb16a60903bc712dc9465eb75cf91b429533081d8`。上游声明 0 项及消费者 1 程序口径保持不变；原有整体finish失败/旧标记不改写为成功，比赛worker结果必须绑定新HEAD另查。
