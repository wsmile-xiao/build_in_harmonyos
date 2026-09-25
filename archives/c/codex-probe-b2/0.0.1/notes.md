# codex-probe-b2 0.0.1 鸿蒙适配笔记

## 环境信息
- 操作系统：HarmonyOS 6.0（aarch64，HongMeng Kernel 1.12.0）
- Python：3.12.9（~/usr/local/bin/python3）
- Conan：2.29.1（OHOS 适配版，remote=ohpcd）

## 项目类型
纯 Python、零依赖 CLI 工具（requires-python >=3.10），无需编译、无 ELF 产物。
构建系统：none（源码即产物，仅打包 + 测试）。

## 上游源码确定说明（重要）

任务下发的"上游仓库地址"为未填充的模板占位符（`{{上游仓库地址}}`）。
通过以下证据链确定上游为 https://github.com/leiMizzou/codex-probe（commit 579b6b0）：

1. 仓库内已有同系列已合入归档 codex-probe-b3/0.0.1，其 conandata.yml 指向
   leiMizzou/codex-probe commit 579b6b0 的 tarball（sha256 99ca4882...077d）；
2. 该 commit 是 leiMizzou/codex-probe main 分支最新提交（2026-05-28），仓库仅
   main 分支、无 tag/无 fork，源码稳定可复现；
3. 本机实测下载 tarball，sha256 与 b3 归档声明值逐字一致；
4. 全网检索（GitHub API 搜索、AtomGit/gitcode/gitee、Sourcegraph、Bing/DDG）
   不存在名为 "codex-probe-b2" 的独立公开仓库；b2/b3 为平台侧对同名仓库
   codex-probe 的消歧派生名（同系列另有 JamesChan21/codex-probe 已归档为
   codex-probe/1.0.3，Go 实现，非本包来源）。

> 版本号 0.0.1 为任务指定（上游 pyproject 自述 0.1.0，无发布 tag；
> 与 b3 同口径取任务指定版本）。

## 语言预检说明（R47 记录）

源码语言为 Python（三级判定：无 manifest 构建系统、无 C/C++ 源、100% .py）。
任务显式指定适配 codex-probe-b2 且同系列 Python 包（codex-probe-b3）已被平台
合入，适配形态为"应用打包 + 测试"而非 C/C++ 交叉编译，故不适用 R47 的
env_unsupported 终止路径（该规则针对 ECS 派发的非 C/C++ 源码误派场景）。

## 构建步骤
1. conandata.yml 声明官方源 tarball（codeload 直链，sha256 校验一致）
2. conanfile build() 内直接运行上游 unittest 套件（层1门禁，
   docs/TEST_QUALITY_SPEC.md 层1必做；monkey-patched urlopen 无真实网络）
3. package() 打包 .py 入口 + codex_probe_data 基线数据 + 文档/LICENSE

## 测试

### 上游测试（81 项）
- 框架：unittest（tests/ 目录，test_http_retry 9 + test_scoring 56 + test_validators 16）
- 本机实测：`PYTHONPATH=$SRC python3 -m unittest discover -s tests -t . -v`
- 结果：Ran 81 tests in 0.010s, OK（81/81，100%）
- CI 集成：build() 内 `sys.executable -m unittest discover -s tests -t . -v`，
  conan create 自动执行，失败即构建失败

### 鸿蒙消费者测试（7 项）
- 运行：conan create 时自动执行 test_package
- 覆盖：provider_probe 导入、CLI --help、基线数据解析、list-baselines 子命令、
  audit 子命令、OHOS 平台指纹、Python 版本 >=3.10
- 结果：7/7 通过

## 平台指纹
- platform.system() = HarmonyOS
- platform.machine() = aarch64
- Python = 3.12.9

## 已知限制
- audit 子命令需对目标 endpoint 发真实 HTTP 请求，消费者测试仅验证其命令面
  （--help），不做真实网络审计（CI 环境无可用中转站）
- 上游 pyproject 版本自述 0.1.0，包版本取任务指定 0.0.1（与 b3 同口径）
---

**编译结束**: 2026-09-23 16:24
**最终状态**: built
