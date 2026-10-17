# 草稿 — 隔离 job 陈旧 CI profile 缺 PATH 注入：build 阶段工具 127（设备上工具其实存在）

> Status: **Draft**（待审核 promote）| severity: `2` | category: `ci, conan, environment, shadow-ci` | Updated: 2026-09-27
> 对应: `knowledge/drafts/DRAFT-libuinputplus-0.1.4-shadow-job-stale-ci-profile.kv`

## 可复现症状与稳定错误签名

- `/system/bin/sh: cmake: inaccessible or not found`，紧随 `libuinputplus/0.1.4: Running CMake.configure()` 出现，`ConanException: Error 127`
- 关键定位特征：**L0 门禁已过、conan create 已推进到 package build() 才 127**（不是 conan 起不来，也不是 test_package 阶段）。

## 根因与最小复现

- 触发实例：libuinputplus 0.1.4 真机 shadow CI r2（2026-09-27，job `libuinputplus-0.1.4-20260927`，repo-source 取自 simh job 的 repo）。
- 设备无 git，隔离 job 的 repo 靠 `--repo-source` 链式复制，是**创建时刻的陈旧快照**：其 `ci/conan/profiles/ohos-aarch64` 的 `[buildenv]` 段只有 CONFIG_SHELL/SHELL 两行，缺现行 main 的 `PATH=+(path)/data/service/hnp/bin` 与 `LD_LIBRARY_PATH=+(path)/.../llvm/lib` 注入。
- conan 的 conanbuild 环境因此不含 hnp/bin，`CMake.configure()` 子进程找不到 cmake，exit 127。
- 最小验证：`ls /data/service/hnp/bin/cmake` → 存在（证伪工具缺失）；`grep -A3 buildenv <job repo>/ci/conan/profiles/ohos-aarch64` → 无 PATH 注入行（确认陈旧）。
- 与 E307 的边界：E307 是目标机**真的没装** cmake（test_package 阶段，方案是绕开 cmake 用 profile 编译器直编）；本条工具存在、失败在 build 阶段、根因是沙箱基础设施陈旧——照搬 E307 的直编方案会掩盖问题且对本例（必须用 CMake 的库）不可行。

## 已尝试方案（含失败方案及结果）

| 方案 | 结果 |
|---|---|
| 按报错提示怀疑“鸿蒙上编译器/工具兼容性” | 排除：127 是找不到可执行文件，不是编译报错 |
| 怀疑设备缺 cmake | 证伪：`ls /data/service/hnp/bin/cmake` 存在；polly/picolibc 等 CMake 包此前在同设备构建成功 |
| 刷新沙箱内 profile 为当前 main 版本后重跑（采纳） | r3 起 cmake 正常调用，进入真实编译 |

## 最终方案、输入输出与真实验证

- 输入：本机 worktree（origin/main 基线）的 `ci/conan/profiles/ohos-aarch64`。
- 处理：scp 覆盖设备上 job repo 内的同名 profile 副本（仅沙箱副本，不进 PR、不动 git 内容——PR 基线是 CI worker 的现行 main）。
- 输出：conanbuild 环境恢复 PATH/LD_LIBRARY_PATH 注入。
- 真实验证：r3–r5 连续三轮 conan create 完整走通（configure→build→install→test_package），r5 exit 0 全门禁通过。

## 适用范围、反例、解除条件与风险

- 适用：所有真机 shadow CI 隔离 job（`--repo-source` 是标准流程，链式陈旧是结构性风险）；任何“工具在设备上存在但 conan build 环境找不到”的 127。
- 反例：登录 shell 里 `command -v cmake` 找不到 ≠ runner 失败（runner 环境与登录 shell 不同）；目标机真缺工具时回 E307。
- 解除条件：job 创建脚本改为从当前 main 重新同步 repo（或设备装 git 可 clone）后，本条风险消失。
- 风险：每次刷新 profile 都要确认来源是当前 main，否则沙箱结果与真实 CI 基线脱节；profile 里含设备特定路径，**绝不能**把沙箱版 profile 提交进 PR。

## 知识库查重与新增价值

- grep index.tsv：E307（cmake 127——目标机真缺工具、test_package 阶段、绕开 cmake）。无“repo-source 陈旧快照/profile 注入缺失”条目。
- 新增价值：①给出 127 失败的**两步鉴别法**（ls 工具是否存在于 hnp/bin + grep 沙箱 profile buildenv）；②修复动作明确为“刷新沙箱副本、不进 PR、不改配方”（守住 R33 与基础设施边界）；③指出链式 repo-source 的结构性陈旧风险及治本方向。
