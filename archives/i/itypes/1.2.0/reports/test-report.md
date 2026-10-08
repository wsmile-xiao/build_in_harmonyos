# itypes 1.2.0 测试报告

> **项目**：itypes 1.2.0
> **测试日期**：2026-09-28
> **测试环境**：OpenHarmony PC aarch64，H1 目标设备；上游测试沿用 H1-001 不变输入证据
> **测试类型**：上游单元测试、Conan consumer 集成测试、官方 W3 本地验证

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:--|--:|--:|
| 唯一测试定义 | 12 | 100% |
| 通过 | 12 | 100% |
| 失败 | 0 | 0% |
| 跳过 | 0 | 0% |

11 个上游测试来自未修改的固定 `tests.py`；H1-001 已通过 11/11，测试源与候选 002 相同，本轮按项目规则复用，没有重复运行。新增 1 个 Conan consumer 集成测试定义，在 H1-002 的 G2 和 W3 阶段各执行一次；两次均为 1/1 调用成功、7/7 场景组通过、17/17 字面断言通过。两次执行是同一个测试定义，不重复计数。

## 二、结论与限制

测试输入及 consumer 检查通过，但官方 `finish` 未完整通过，不能据此宣称候选已完成全部验收。H1-002 的 `finish` 与 runner 均返回 rc 1：G0 因固定源码没有 `configure`，运行 `./configure` 得到 rc 127；该检查在 finish 中非阻塞。G1–G4 均报告 PASS，Conan G2 经 HTTPS 获取固定 sdist 并通过 consumer；W3 的 `setup.sh` 与 `build_and_test.sh` 返回 rc 0。

原 finish 的 submit readiness 当时缺 `.staging-verified`、`packaging/`、软件级 `README.md` 和本测试报告；README、报告与 notes 对话记录现已补齐，但原始 finish 结果未重跑。H1-003 确认公开旧 `package` 命令未注册；固定 SKILL R19 规定以 Conan `create` + `upload` 发布并禁止手动 tar。H1-002 的 Conan create 已通过，upload 留给 PR 合入后的 release 流程。旧 staging marker 属 R19/R20 已废弃路径，不作为当前 PR 门槛。该纯 Python 包没有 native ELF/debug symbols。官方线上 CI 未运行。

资格与任务元数据：账号 `gcw_tlRDjnsx` 的 OpenHarmony 项目成员权限已于 2026-09-28 核验为 Developer/write/active，回执位于 `members/gcw_tlRDjnsx/evidence/project-role-20260928.json`。赛事任务当前标签为 `cpp`，固定上游源码为 Python；按人工参赛 Conan 路径如实提交并披露该不一致作为元数据与计分风险，不声称已获得普遍语言豁免或积分保证。

## 三、测试详情

| 测试项 | 输入 / 证据 | 结果 |
|---|---|---|
| 上游单元测试 | 固定测试归档 SHA-256 `0e62f24639beec41d503cb20dba5b87e4395966ebb70bbfe7393c0b5a32bb5d9`；H1-001 | 11/11 PASS，rc 0；候选 002 输入未变，复用证据 |
| Conan G2 consumer | 候选补丁 SHA-256 `8b457dbb91dceb12f18147781b85540abbebd28b54e76eb033e66ff232153329`；H1-002 | 1/1 调用、7/7 场景组、17/17 断言 PASS |
| W3 consumer | H1-002 官方 `setup.sh` + `build_and_test.sh`；`.ci-result.json` 日志 SHA-256 `eb26550c9582ac393be07ae54f1621a0c3e4b622a1178bd64bdef671d856ac31` | W3 rc 0；1/1 调用、7/7 场景组、17/17 断言 PASS |
| 官方 finish | H1-002 原始 `finish.log` 与 `RESULT.md` | rc 1；G0 `./configure` rc 127；最终步骤 step5b、step8 未通过 |

G1、G2、G3、G4 的官方配方/质量报告均为 PASS。W3 使用固定 sdist 的私有预下载缓存；G2 为真实 HTTPS 下载。相关知识参考为 E410：consumer 验证包安装后的 API 语义，而不是只验证 import。以上结果不等于官方线上 CI 通过。

finish 的失败步骤含义按固定源码区分：`step5b` 是 W5 全局知识完整性检查，日志列出 E219、E253、E305 的全局必填字段缺失，并同时显示 itypes 本库没有待补知识；`step8` 是旧版 submit-readiness 检查。它当时缺测试报告、`packaging/` 和 `.staging-verified`，其中测试报告现已补齐。`packaging/` 和 staging marker 属于 R19/R20 已废弃路径，不据此制造 tar 或 marker；原 finish rc 1 保留。

## 四、证据位置

- H1-002 结果记录：`members/gcw_tlRDjnsx/evidence/itypes-h1-002/RESULT.md`。
- H1-001 上游测试结果：`members/gcw_tlRDjnsx/evidence/itypes-h1-001/RESULT.md`。
- H1-002 完整原始回收包 SHA-256：
  `a6838df4caa3a65ed9bff8d1bc9be8e407b33e9ccf0a4c932518edd73f95a561`。
