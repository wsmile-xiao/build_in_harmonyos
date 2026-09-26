# SKILL 执行流程反馈报告

## 背景
- 软件 / 版本：slay 3.0.2
- 构建系统：无（POSIX shell 无扩展名 CLI，直接安装）
- 上游仓库：https://salsa.debian.org/debian/slay.git
- 适配路径：路径 A；补丁：0；Conan 编译依赖：0
- 状态：本地 Conan 验证与 W3 通过，远程审查和 CI 待执行

## 情况
### 执行概要
| 阶段 | 结果 | 证据 |
|---|---|---|
| init-build | 源码下载完成；把无构建工程错判 autotools | `archives/s/slay/3.0.2/notes.md` |
| 语言复核 | 只读检测返回 `other`，人工确认 `#!/bin/sh` 脚本主体；按纯脚本可接受政策继续 | `knowledge/drafts/E6401-draft-1AD8.md` |
| conan-verify | PASS；Conan create + 真正运行 test_package 的 3/3 安全 CLI 测试 | `reports/conan-create.log`（本地不入仓） |
| finish | W3 PASS；G0 因不存在 configure 报非阻塞假失败；旧式 packaging/ 与知识关联的门禁告警见 notes | `reports/w3-local-ci.log`（本地不入仓） |
| submit / CI | PR 创建前阶段，结果待机器人返回；不会把待运行写成通过 | 本轮交付表 |

### 失败与问题
- G1 初次拒绝零编译配方：`conanfile.py 缺少: build() 方法`、`export_sources()`、补丁调用；显式添加合法空编译阶段后 G1 和 G2 均过。见 `archives/s/slay/3.0.2/conanfile.py:22-30`。
- `finish` G0 仍根据初始化的 autotools 判型执行 `./configure`，实际返回 `./configure: No such file or directory`；G2/W3 使用真实 Conan 配方均通过，不将 G0 错误写作构建成功。
- `finish` 摘要生成在现有全仓索引解析过程中报 `'str' object has no attribute 'append'`；不修改共享 `scripts/` 或 `SUMMARY.md`。`packaging/`/发布 tarball 属旧版检查，Conan 流水线不交付 tarball。
- debconf 是 Debian 配置脚本依赖，`slay` 主程序不依赖；制品仓查询 `debconf/1.5.91` 返回系统加速策略错误，未声称已发布或未发布。

### 知识图谱与测试
- engine 命中 E325（bash 与临时目录），不直接适用于 POSIX sh；正式条目 E165 指出 OHOS 缺少 `/bin/sh`，因此只在打包副本中改为 `/system/bin/sh` 并补 PATH，消费者测试核对包内产物；对比 `DRAFT-dshlibs-0.109-lang-preflight-pure-script-package-misdetect`：其误报 `c`（有 Makefile），本次误报 `other`（无 Makefile）。新增 `E6401-draft-1AD8`，draft-review 建议 `create`，graph validate 通过（旧条目 warning 不属于本次变更）。
- 上游无自动测试：tests/ 0、ctest 0、pytest 0；新增消费者测试 `3/3` 安全输入检查（均覆盖同一无目标 usage 分支），固定 `SLAY_BUTTHEAD=off`；在 x86_64 宿主运行 POSIX shell 解释器，非 aarch64 实机，不适用 qemu；未测杀进程分支。
- W4 初审指出完整 GPL-2 正文缺失及草稿占位符 shell 重定向风险；已将 Debian copyright 指定的 GPL-2 全文纳入配方输入并修正可执行示例，待复审。

### AI 检视结果
- 摘要、行级意见与处理：提交前暂无；只在收到结果后按事实处理，不为报告措辞推送新 commit。

### CI 结果
- 本地 W3：PASS；远程 PR CI：待触发，不写 PASS。

### 效率分析
- 初次 G1 失败后修复一次；W3 一次通过；无 CI 修复轮次。关键瓶颈是纯脚本被误判 autotools / `other`，以及 `finish` 旧 packaging/ 假门禁。无必要的源码补丁。

## 建议
### SKILL 设计改进
- `scripts/ohc/finish.py:360-408` 的 submit-readiness 将废弃 `packaging/` 非空与 `.staging-verified` 列为失败：对仅交付 Conan 配方的项目应以 `conan create` W3 证据为准；`clean-verify` 应支持无 configure 的 install-only 脚本，而不将其判为编译失败。

### 模板改进
- `templates/conanfile-headeronly.py.tmpl` 的脚本变体与 `conan-verify` G1 所要求的 `build()`、`export_sources()`、`apply_conandata_patches(self)` 不一致；补上这些方法的可选安全示例，并在脚本变体明确 `package_type=application`、`cpp_info.bindirs=["bin"]`、基于实际脚本测试，避免生成 autotools/CMake 假测试。

### 自动化补全
- `scripts/ohc/lang_detect.py:95-159` 应识别无扩展名 shebang 主程序，且不一律排除 bash 主体；`scripts/ohc/summary.py:84-89` 应在 `.append()` 前保证解析值是 list，避免全仓既有索引里的 scalar 扰动。`init-build` 应以 configure/Makefile 是否真实存在修正 build_system，反馈采集器应避免 `{BUILD_SYSTEM}` 原样输出及测试数恒 0。

### 知识图谱覆盖
- 已填 `knowledge/drafts/E6401-draft-1AD8.kv/.md`：无构建文件、无扩展名 `#!/bin/sh` 主体 → `other`，区别于 d-shlibs 的 Makefile → `c`。主编可审查后 promote 或合并到现有纯脚本误判条目；本 PR 不动正式图谱。

## 作者
- 姓名：lkjing2021345
- 邮箱：1908499668@qq.com
- Agent ID：1AD8
- PR 编号：提交前尚未创建
