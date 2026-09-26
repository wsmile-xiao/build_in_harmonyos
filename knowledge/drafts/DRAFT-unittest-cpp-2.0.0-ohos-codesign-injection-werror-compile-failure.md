# DRAFT — OHOS 工具链注入 `-Wl,--code-sign` × 上游强制 `-Werror`：编译期 unused 告警升级成硬 error

- **草稿 ID**：`DRAFT-unittest-cpp-2.0.0-ohos-codesign-injection-werror-compile-failure`
- **来源**：unittest-cpp 2.0.0（任务 11521，分支 `feat/unittest-cpp-2.0.0`，HarmonyOS PC 真机）
- **状态**：DRAFT，待人工审核 promote

## 一句话

HarmonyOS 编译 wrapper 为产物签名全局注入 `-Wl,--code-sign`（链接期必需）；clang 在
**编译阶段**把它判为 `unused-command-line-argument` 告警，凡上游把 `-Wall -Wextra
-Werror` 硬编码进自身编译规则的工程，**每个源文件第一条编译行即炸**，make Error 1。
首选解 = 上游自带的警告降级 option（零补丁）；次选 = 精确追加
`-Wno-error=unused-command-line-argument`。**绝不许删/过滤 `--code-sign`。**

## 可复现症状（稳定错误签名）

```text
clang-15: error: -Wl,--code-sign: 'linker' input unused [-Werror,-Wunused-command-line-argument]
make[2]: *** [CMakeFiles/UnitTest++.dir/build.make:79: .../AssertException.cpp.obj] Error 1
```

触发条件（vramsteg 系等纯 CMake 工程不炸、本包炸的对照原因）：
1. OHOS 工具链构建（注入 `-Wl,--code-sign` 进编译与链接命令行）；
2. 上游将 `-Wall -Wextra -Werror` 写死进自身规则（unittest-cpp：
   `option(UTPP_AMPLIFY_WARNINGS "..." ON)` + `set(CMAKE_CXX_FLAGS "... -Wall -Wextra -Werror")`）；
3. 工程无（或难以利用的）外部 CFLAGS 注入缝 —— flags 被上游 set 语义固化。

## 根因与最小复现

- clang 对出现在编译阶段的 `-Wl,` 参数产生 unused 告警属既定行为；`-Werror` 将
  **任何**告警升级为 error，注入参数因此致命化。glibc/Linux 构建不会复现
  （无 code-sign 注入）。
- 最小复现：取任一硬编码 `-Wall -Wextra -Werror` 的 CMake 工程，在 OHOS 工具链下
  直接 `cmake --build` → 每条编译行首错即为本签名。

## 已尝试方案（含失败）

| 尝试 | 结果 |
|------|------|
| 原样构建（默认 UTPP_AMPLIFY_WARNINGS=ON） | ❌ 全部源文件 `linker' input unused [-Werror,...]` |
| 删除/过滤 `--code-sign` | **禁止**——链接期签名必需，产物失去 `.codesign` 即设备拒载/CI 签名门禁红（本末倒置） |
| 全局 `-Wno-error` | 不取——掩盖其余真实源码告警，评审面大 |
| **官方开关降级（推荐）** | ✅ `-DUTPP_AMPLIFY_WARNINGS=OFF` 后 configure/build/上游 268 例测试全绿 |
| 兜底 `-Wno-error=unused-command-line-argument` | ✅ 可用（本包未走：上游有官方开关；类别精确不掩盖他警） |

## 最终方案与真实验证

配方 `generate()`：`tc.cache_variables["UTPP_AMPLIFY_WARNINGS"]="OFF"`（连同
`CMAKE_POLICY_VERSION_MINIMUM=3.5` 解 2.8.1 版本声明通道）。设备实测：
构建通过 + 上游 `Success: 268 tests passed.` + 消费者 4/4；**零源码补丁**。

## 适用范围 / 反例 / 风险

- **适用**：任何满足上述三条件的上游（候选高发面：老 CMake 工程带
  `WERROR/AMPLIFY/PEDANTIC` 类 option；Makefile 写死 `CFLAGS += -Werror` 的
  suckless 系等——遇 CFLAGS `+=` 固化时注入缝无效，本条为主解）。
- **反例（不属本条）**：
  ① 源码语义类告警被 -Werror 放大（int-conversion/implicit-function 等）→ 走
  既有 **E063**（按类别 `-Wno-error=X` 追加 CFLAGS，有注入缝）；
  ② 工程有可用 CFLAGS 注入缝且上游未硬编码 -Werror → 通常根本不触发。
- **风险**：低。降级的是上游"警告放大策略"，不改任何源码告警事实；保留其余类别。

## 查重与新增价值（四范围 + draft-review）

- 查重（2026-09-24）：`knowledge/graph/index.tsv` 对 `code-sign/unused-command-line`
  **0 命中**；`经验文档/适配经验汇总.md`、`适配检查清单.md`、`B草稿库/` 对
  `code-sign` 0 命中；`-Werror` 相关既有 E063（源码告警族）与 automake
  `AM_PROG_AR`（经验汇总 §889，不同签名）均不覆盖"工具链注入参数被 -Werror 放大"。
- draft-review 若提示 E063 相似：两者**触发面（平台注入 vs 源码语义）、错误类别
  （unused-command-line-argument vs int-conversion 族）、修法优先级（上游官方开关
  vs CFLAGS 追加 -Wno-error=X）三维全不同**，且常无 CFLAGS 缝的工程 E063 解法不可达
  ——按 §6.2 组合型知识不判重，报 create，`similar_to: E063` 互指。
- 新增价值：给出"签名参数不可删"的红线 + 修法优先级序列，防止窗口在 -Werror 类
  失败面前走"删注入参数/全局关警告"两条歧路（各有真实代价）。

## 关联

- 同 PR 实证包：`archives/u/unittest-cpp/2.0.0`（notes.md「适配中撞到的真实问题」表 001）
- 同 PR 关联 Issue：见 PR 正文 `- **关联 Issue**` 回填
- 姊妹通道（同 PR 不同包先例）：`DRAFT-vramsteg-1.1.1-cmake4-explicit-old-policy-guard-hard-error`
