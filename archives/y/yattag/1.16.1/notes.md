# yattag 1.16.1

## 软件与配方

- 纯 Python HTML/XML 文档与表单生成库，不含本机扩展。
- 配方从 PyPI sdist 安装 `yattag` 模块及 `py.typed`，并打包 LGPL-2.1 许可证文件；设置 `YATTAG_SOURCE_ARCHIVE` 时校验摘要并使用固定本地包。
- 上游元数据仅在 Python 3.5 以下条件声明 `typing`；本配方未声明 Conan 依赖。H1 #004 设备环境为 OHOS Python 3.12.9。
- 竞赛平台当前语言标签为 `cpp`，但本软件上游源码为 Python；按已确定的人工参赛路径继续并披露此差异，不修改平台标签，也不将此解释为官方通用豁免。
- 本候选未使用知识图谱条目；manifest 的 `knowledge_gained` 留空，避免把未引用的一般事实登记成知识成果。

## 当前状态

状态：built。已发布 head `ac332226cbed49aba097570eb03cdd32cf8427a1` 的官方 CI #63990 通过，但 2026-09-30 正式评审因 PR 正文编译字段与鸿蒙消费者用例退回。H1 #005 在 OHOS Python 3.12.9 / Conan 2.29.1 上验证十文件候选树 `9241d2a7e8759a1bd24335f1ec468a6b8044a215`：G1/G2/G3、真实 Conan 包及原消费者 `functional.py` 和新增 `ohos_document_roundtrip.py` 分别通过；后者从真包导入，生成 HTML，在 Conan 私有构建目录完成 UTF-8 文件写入、读回和内容解析。两个消费者合计 2/2 场景、3+4 条检查；内置 W3 RC0。完整 `finish`、runner、外层进程仍 RC1，具体历史及本轮失败见下方原始回执，不能称完整门禁通过。H1 原始报告留在本地证据归档，PR 仅提交配方、测试与必要说明；新 head 官方 CI/AI 尚待 PR 更新后回读。

旧候选 H1 #001 固定树 `03e31d731a9b20b77e05b7565181b18ecee1ceb1` 的证据：OHOS Python 3.12.9 上游 unittest 28/28 通过；真实 `conan create` 与消费者 1 场景、3 条断言通过。该次完整 `finish`/runner 返回 1，日志列出的失败步骤为 `step3, step5b, step8`：step3 的 Conan G1 报告缺少 `export_sources()` 和 `apply_conandata_patches(self)`；step8 的 submit 就绪预检要求旧 `packaging/` 和 `.staging-verified`，不符合固定框架 R19/R20；finalize 另有旧 release/debug tar 缺项及 notes 对话记录缺项。保留 `step5b` 原始失败编号，不对其原因作无证据归因。旧 step8 与 finalize 的旧式打包/staging 要求不作为当前 PR 门槛；其历史失败仍保留，不称为完整 finish 或 CI 通过。旧候选 G0 因纯 Python sdist 无 `configure` 文件返回 127，按真实结果保留。

H1 #004 的 `step5b` 全局知识扫描发现框架基线 `E219.kv`、`E253.kv` 的空 `root_cause`，以及 `E305.kv` 的空 `root_cause`、`rec_approach`。yattag 本地 W5 检查通过：`notes.md` 提取 0 条、待处理 0 条，`manifest.yaml` 知识条目 0 条、未引用 0 条；不修改无关全局知识条目。`step8` 仍要求旧 `packaging/` 和 `.staging-verified`，finalize 仍报告旧 release/debug tar 缺失及 notes/manifest 状态不一致。按固定框架 R19/R20，不生成旧式 tar、package 目录或 staging 标记；保留原始失败与返回码，不据此声称完整 finish。G0 对纯 Python sdist 寻找 `configure` 返回 127，仍作为独立真实失败披露。

上游源码与测试输入未变，可复用 H1 #001 同一 sdist 的 OHOS unittest 28/28 结果，但本轮未重跑。H1 #005 已按现行 Conan 路径完成 G1/G2/G3、真实 Conan create/package/两个 test_package 消费者与本地 W3。不得调用已废弃的 `ohc-run.py package`，不得手工上传、生成旧式 tar 或 staging 标记；本地验证不等于新 head 官方 CI 或发布。

### 对话 #12275 / H1-001

回读 H1 #001 报告与归档包：旧候选 G0 `rc=127`，Conan G1 失败，W3 `conan create` 及消费者通过，完整 finish `rc=1`。团队本地保留该次原始回执与证据包；它们不在本 PR 内。

### 对话 #12275 / H1-002

H1-002 固定请求包已过时、未执行，因其包含已废弃 package/tar/staging 要求而撤回；保留原件供审计。不得把旧 step8 检查当作新候选阻塞。

### 对话 #12275 / H1-003

H1-003 在唯一 H1 私有克隆应用九文件候选补丁后，`git diff --cached --check` 因补丁文件行尾 CRLF 报 `README.md:1–13 trailing whitespace`，runner/outer RC 2；官方 finish、Conan 和 W3 均未启动。团队本地保留原始回执与归档（SHA-256 `fc9f604d6be7d0b6cbd5bb324a754cf4c2db6d52893adc9676c6794a14c8b9fe`）。本轮仅修正固定 diff 包的 LF 行尾，不改软件内容，不重播 H1-003。

### 对话 #12275 / H1-004

H1-004 已于 2026-09-28 在唯一 H1 新私有根单次执行并自然结束，团队本地保留其输入、设备环境和原始结果。G1/G2/G3、Conan 包、旧消费者和本地 W3 通过；G0 RC 127、step5b/step8、finalize 与完整 finish/runner/outer RC 1 如实保留。不得重播 H1-004。

### 对话 #12275 / H1-005

H1-005 于 2026-09-30 在唯一 H1 新私有根单次执行并自然结束。团队保留原始回执与完整日志，归档 SHA-256 为 `016de531c70743ad379e2e84559e1fd99f28ab53cc37b5c0eeb91683254310cd`；该归档不在本 PR 内。固定十文件候选树 `9241d2a7e8759a1bd24335f1ec468a6b8044a215` 的 G1/G2/G3 和内置 W3 通过，真实 Conan `test_package` 的两个独立消费者分别输出 `PASS packaged import, version, and HTML escaping` 与 `PASS packaged HTML generation, UTF-8 file round-trip, and parsed content`；新增 OHOS 文档消费者在 `self.build_folder` 完成文件往返及解析。固定 sdist 未变，沿用 H1-001 上游 28/28，H1-005 未重跑上游套件。G0 对纯 Python sdist 找不到 `configure` 返回 127，`finalize-archive` RC2，旧全局 W5 字段和 staging/step5b/step8 失败仍在；完整 `finish`/runner/outer 均 RC1。本次未执行官方 CI、制品上传或远端 PR 写入，不重播 H1-005。
