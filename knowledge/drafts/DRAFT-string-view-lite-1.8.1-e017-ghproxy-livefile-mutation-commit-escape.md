# DRAFT — E017 镜像注入恢复失败污染活文件 conandata.yml 并被 submit 自动提交：守卫域名白名单缺口与正确基线捕获

> 状态: 草稿（基于 string-view-lite 1.8.1 / 任务 #5901 真实证据，2026-09-05）。
> 依据: 铁律 R39（官方源）、R6/R10（生成文件）、E017（ghfast/gh-proxy 镜像注入）、AGENTS.md 第 4 节（基线与脏状态）。

## 真实问题（场景，含可复现症状）

string-view-lite 1.8.1 适配（header-only，github 拉源）期间，`conan-verify`/`finish`（W3）
触发的 E017 机制在运行期把 `conandata.yml` 的官方 sources URL 临时改写为镜像列表以完成
`conan get()`。与既往记录的旁文件残留不同，本次出现三个新失效面：

1. **活文件被改写且恢复静默失败**。运行日志明确打印 `🔄 已恢复原始 conandata.yml`，
   但工作区 `conandata.yml` 实际停留在注入形态（可复现症状 = 稳定错误签名）：

   ```yaml
   sources:
     url:
       - "https://gh-proxy.com/https://github.com/martinmoene/string-view-lite/archive/refs/tags/v1.8.1.tar.gz"
       - "https://github.com/martinmoene/string-view-lite/archive/refs/tags/v1.8.1.tar.gz"
   ```

   （url 从标量变为列表；官方 URL 仍在列表内，sha256 不变，因此 conan 全流程绿灯，
   极难从构建结果察觉。）

2. **守卫域名白名单缺口**。`scripts/ohc/conan_verify.py` 的恢复守卫条件是
   "当前文件含 ghfast.top 才回滚"（v12.17 引入）；本次注入域名为 **gh-proxy.com**，
   守卫不命中 → 不回滚。注入域名集合（gh-proxy.com/ghfast.top/moeyy.cn/kkgithub.com 等，
   见 PF7 镜像黑名单 14 域）大于守卫匹配集合。

3. **污染被 submit 自动 git add 带入已推送提交**。工作区污染后继续走
   finish → W4 → submit 流程，submit 的自动 `git add` 把污染的 conandata.yml 一并提交
   （commit `ed1b4714e9` "feat(string-view-lite): 1.8.1 适配完成"）并 `git push` 到
   远端分支——残留从"工作区噪声"升级为"远端可见的 R39 违规"。

## 根因

- E017 恢复路径：守卫条件以单一域名（ghfast.top）匹配注入痕迹，而注入域名集合更大；
  且恢复成功与否只靠日志声明，无"恢复结果自检"（恢复后 diff 是否回到官方标量形态）。
- 提交路径：submit 自动 `git add` 先于人工核对 diff（AGENTS.md 第 8 节要求"精确暂存并
  人工核对 diff"，自动化路径绕过了这道人工闸）。
- 基线噪声：共享仓库的本地 `main` 落后 `upstream/main` 1646 个提交，W3 junk_check（JC6）、
  create-pr 内嵌 preflight（`main...HEAD`）把上游存量数百个 conandata.yml 误算为"本次变更"，
  全量扫描既误报（JC6 报 31 个包、PF7 报数百条他人归档违规）又超过 submit 给 create-pr 的
  30s 子进程超时——这就是两次"创建 PR 命令超时（30s）"的真实根因（非网络故障）。

## 已尝试方案（含失败方案及结果）

| # | 方案 | 结果 |
|---|------|------|
| 1 | 信任"已恢复原始 conandata.yml"日志，直接走 submit | 失败：污染被自动 git add 提交为 ed1b4714e9 并推送（本次事故本体） |
| 2 | 直接重试 submit/create-pr（CLI 基线 main 过期） | 失败：PF7 全量扫描数百条他人归档违规 + 超过 30s 子进程超时，两次超时 |
| 3 | 手动 `gitcode_pr.py create-pr`（绕过 submit 的 30s 包装） | 失败：同样卡在全量基线 preflight，数百 PF7 违规拦截 |
| 4 | **用正确基线调用 `run_preflight(repo, "upstream/main", "HEAD")`** | 成功定位：报告唯一违规正是本次变更中的 conandata.yml gh-proxy.com 残留（基线对比隔离法） |

## 最终方案、输入输出与真实验证

1. **捕获**：以正确基线跑 preflight（输入=`upstream/main...HEAD` 变更文件清单），
   输出 PF7 精确指认 `archives/s/string-view-lite/1.8.1/conandata.yml:6 镜像前缀 gh-proxy.com`。
2. **修复**：`git show b942b9fba5:<path>/conandata.yml > <path>`（恢复官方标量形态），
   `rm -rf .build-cache/`，精确 `git add` 单文件，新提交 `5cb4d39586` 修复并 push
   （不 force-push）。输出：`upstream/main...HEAD` 基线下 **PF1-PF9 全部 PASS**；
   修复提交已推送（ed1b4714e9..5cb4d39586）。
3. **验证**：修复后 `run_preflight(..., "upstream/main", "HEAD")` 返回 `(True, [])`；
   归档 conan-verify G0-G4/L2/L4/L5 PASS（ctest 4/4、lest 350 用例、test_package 实跑 PASS）
   在污染修复前后均成立（sha256 未变，官方 URL 属于注入列表成员，构建内容一致）。

## 适用范围、反例、解除条件与风险

- **适用**：所有 github 拉源失败触发 E017 的包；凡注入域名 ≠ 守卫白名单（ghfast.top）时，
  活文件可能以镜像列表形态残留；任何自动 git add 的提交路径都可能把残留带入提交；
  本地 main/origin/main 落后的共享仓库中，JC6/preflight 增量基线必然产生全量误报。
- **反例**：注入域名恰为 ghfast.top 时守卫正常回滚（v12.17 既有行为）；本地 main 与
  upstream/main 同步时 CLI preflight 基线正确，无需绕行。
- **解除条件**：框架修复（守卫域名集合扩展 + 恢复结果自检 + submit 自动 add 前置正确
  基线 preflight）落地后，本条降级为历史参考。
- **风险**：镜像列表形态官方 URL 仍在列表内，构建/测试全绿，极易漏检——必须以
  preflight/PF7 或 `git diff` 文本级核对，不能依赖构建结果。

## 查重与新增价值

| 既有条目 | 覆盖内容 | 与本条的差异 |
|----------|----------|--------------|
| E017 | 镜像注入机制本身 | 不覆盖恢复失败与提交逃逸 |
| DRAFT-lexy-2025.05.0-e017-mirror-injection-residual-cleanup | 注入生成的**旁文件**残留（.ghfast-bak/.orig/.lock/.build-cache）识别与清理 | 本条是**活文件** url 标量→镜像列表改写 + 恢复静默失败 + 污染进入**已推送提交**，处置手段也不同（正确基线捕获 + 新提交修复，而非 rm 残留文件） |
| DRAFT-E323-conan-verify-ghfast-bak-rollback | .ghfast-bak 崩溃恢复把**旧 bak** 覆盖当前 conandata | 本条无 bak 参与，是注入本体残留；且揭示守卫域名白名单缺口正是 E323 场景修复（v12.17）引入的新失效面 |
| E415 | CI build_and_test.sh 在 conan create 前对官方 url 单值做镜像改写（CI 侧机制） | 本条发生在本地 conan-verify/finish 链路，且核心增量是"恢复静默失败 + 自动提交逃逸 + 正确基线捕获"，与 E415 的 CI 预下载改写互为两侧 |

新增价值：(1) 新错误签名（url 列表形态 + "已恢复"日志假象）；(2) 守卫白名单缺口的
根因定位（框架修复建议可执行）；(3) "正确基线 preflight 隔离真实变更"的通用捕获手法
（同时解释 submit create-pr 30s 超时的真因，避免被误诊为网络故障）。

## 触发实例与验证证据

- 触发：string-view-lite/1.8.1（任务 #5901），污染提交 ed1b4714e9，修复提交 5cb4d39586。
- 证据：`git show ed1b4714e9 -- archives/s/string-view-lite/1.8.1/conandata.yml`（列表形态）；
  两种基线 preflight 输出对比（main...HEAD → 数百 PF7 + 31 包误报；upstream/main...HEAD →
  唯一 PF7 命中本文件，修复后 PASS）；submit6 日志"创建 PR 命令超时（30s）"×2。
- 验证命令：见 `.kv` 的 `verification_cmd` / `rec_command`。
