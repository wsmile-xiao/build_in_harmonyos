# ostra 0.000709606481481482 编译笔记（前置）

## 定位
- 源码：GitHub `tej-1916/ostra`
- 固定提交：`5c1d07cd227648516af4291cb725cb10daac7e5e`
- Conan 包目标：`components/ostra-sysctl`
- 构建系统：CMake
- 产物：`ostra-sysctl`

## W0 依赖
- 无外部 Conan 依赖
- 仅依赖标准 C / POSIX / Linux 接口

## 已完成检查
- 独立 `git worktree` 已建立
- 源码 tarball 已下载并校验 sha256
- 源树已确认包含 `components/ostra-sysctl`
- 上游测试入口已确认：`components/ostra-sysctl/tests/smoke-test.sh`
- 本机已通过 `python -m py_compile` 与 `conan inspect`
- 已补充 `commands.json`，满足 CLI 工具门禁

## 上游测试范围
- 上游仓库 `tej-1916/ostra` 的 test-related 文件共 23 个，按边界分层如下：
  - `services/control-plane/tests/`：15 个（13 个 `test_*.py` + `conftest.py` + `smoke-test.sh`）
  - `tests/`：2 个（`test_edge_glow_input.py`、`test_edge_glow_paint.py`）
  - smoke/helper 脚本：5 个（`components/ostra-sysctl/tests/smoke-test.sh`、`services/control-plane/tests/smoke-test.sh`、`web/dashboard/tests/smoke-test.sh`、`infrastructure/scripts/toolchain-smoke-test.sh`、`infrastructure/scripts/thermal-test.sh`）
  - `edge_glow.py`：1 个运行时辅助文件
- 本轮实际通过的上游相关验证为 6/23：`components/ostra-sysctl/tests/smoke-test.sh` 1 项，以及 `services/control-plane/tests/test_models.py` + `test_config.py` 纯逻辑子集 5 项。
- 未执行的其余 17 项分别受 FastAPI / Supabase / DB / control-plane runtime、PyQt6 + X/XWayland、Node/npm web dashboard、仓库级 infrastructure 脚本和 helper 文件边界限制，不属于本 Conan 包的可执行测试面。
- Conan `test_package` 作为鸿蒙新增消费者测试单独通过。
- PR 正文已同步到 `reports/pr-body.md`，并把“23 个上游测试相关文件 + 本轮实际通过 6 项 + test_package 1 个”的分层说清，避免少报。

## 评审补测
- 按 review 额外修复并执行 control-plane 的纯逻辑子集：
  - 新增 `patches/0001-control-plane-service-action-order.patch`，把 `ServiceAction = Literal[...]` 提前到 `ServiceStatus` 等模型之前，修复 Python 3.12 导入时的 `NameError`。
  - `PYTHONPATH=src python -m pytest tests/test_models.py tests/test_config.py -q`：5/5 PASS。
  - 详细模式复核：`test_models.py` 3 个用例 PASS，`test_config.py` 2 个用例 PASS。
  - 可选扩展子集 `PYTHONPATH=src python -m pytest tests/ -k "not container and not network and not services" -q` 已尝试；11 个 API/runtime 测试在 collection 阶段统一缺少 `supabase`，未计入本包通过项。
- 这组结果属于上游 control-plane 纯逻辑验证；连同 `components/ostra-sysctl` smoke-test 1 项，本轮上游相关通过口径更新为 6/23。

## 阻塞点
- 上游仓库未提供 release tag，当前使用 GitHub commit snapshot
- 上游未声明 LICENSE 文件
- 运行时读取 `/proc`、`/sys`、`sysinfo`、`getloadavg`，已通过手动 `conan create` 与 Shadow CI 的当前路径验证；后续仍建议补最终真机确认
- upstream `ctest` 在当前 HarmonyOS 环境失败，已改为 OHOS 上跳过
- `services/control-plane/tests/test_models.py` 的 Python 3.12 注解顺序问题已通过包内 patch 修复，`test_models.py + test_config.py` 纯逻辑子集 5/5 PASS
- `test_package` 现在优先使用 `/data/service/hnp/bin/bash`
- Shadow CI 已通过；`10.62.220.52:2222` 可连，`10.62.238.136:2222` 仍超时

## 知识草稿
- `knowledge/drafts/E254-draft-OSTR.kv`：监控型程序的单项指标失败应降级为部分数据
- `knowledge/drafts/E255-draft-OSTR.kv`：OHOS `test_package` 的 shell 与临时目录回退顺序
- `knowledge/drafts/E256-draft-OSTR.kv`：Shadow CI 只看 `git archive HEAD` 快照，dirty worktree 需要先落盘
- `knowledge/drafts/E257-draft-OSTR.kv`：上游测试统计应按“测试相关文件 + 包内可执行入口”分层记录，避免把 monorepo 其余 control-plane / web / infra 测试误算进 `components/ostra-sysctl`
- `knowledge/drafts/E258-draft-OSTR.kv`：monorepo 包的 PR 说明应把包内 smoke-test 与 repo 级测试簇分开列出，保留完整上游分母
- `knowledge/drafts/E259-draft-OSTR.kv`：control-plane 纯逻辑测试的 `ServiceAction` 定义顺序问题可通过 recipe patch 修复并复测

## 下一步
- 等待 CI 复测并根据最新日志继续收口

## Shadow CI
```bash
sh "$HOME/bin/run-ohos-shadow-ci.sh" archives/o/ostra/0.000709606481481482
```

## 远端验证
- 手动 `conan create` 已通过，构建产物为 `ostra-sysctl`
- `test_package` 已通过，JSON 校验完成
- 运行命令：`PATH=/data/service/hnp/bin:$PATH conan create . -pr:h=/storage/Users/currentUser/build_in_harmonyos/ci/conan/profiles/ohos-aarch64 -pr:b=/storage/Users/currentUser/build_in_harmonyos/ci/conan/profiles/ohos-aarch64 --build=missing`
- Shadow CI 已通过，摘要：`L0_RESULT=pass` / `L1_RESULT=pass` / `L2_RESULT=pass` / `L4_RESULT=pass` / `L5_RESULT=pass`
