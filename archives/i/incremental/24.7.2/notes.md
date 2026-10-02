# incremental 24.7.2 适配记录（候选）

## 源码与范围

- 固定输入：PyPI `incremental-24.7.2.tar.gz`，28,157 字节，SHA-256
  `fb4f1d47ee60efe87d4f6f0ebb5f70b9760db2b2574c59c8e8912be4ebd464c9`。
- 语言证据：`pyproject.toml` 使用 PEP 517 自定义 in-tree setuptools backend；`PKG-INFO` 声明 Python 3.8–3.12 classifiers 和 `Requires-Python: >=3.8`；固定 sdist 有 19 个 `.py` 文件、没有 C/C++ 源文件。
- 源码为纯 Python，没有 C/C++ 扩展。平台任务记录仍为 `lang=cpp`；依据人工竞赛入口裁决继续，但在 PR 中披露这项差异，不声称已有通用豁免或确定积分。
- Conan 交付范围是纯 Python 核心版本 API：只打包 `incremental/__init__.py`、`incremental/_version.py`、`py.typed` 和 MIT 许可证；不提供 `incremental.update` CLI 或 `_hatch` 集成。
- 固定 sdist 的 `PKG-INFO`/`pyproject.toml` 为完整上游发行版声明 `setuptools>=61.0` 和 `tomli; python_version < '3.11'`，`click>=6.0` 属于可选 `scripts` extra。当前 Conan 包不复制上游 entry-point 元数据，选择只支持不依赖这些组件的核心版本 API；不声称等同完整 PyPI wheel/sdist 功能。`__init__.py` 中的私有项目元数据 helpers 仍来自上游，但不属于本配方支持范围；Python <3.11 的调用可能需要 tomli。直接版本 API 导入仅用 Python 标准库。消费者会检查两个核心模块存在、CLI/Hatch 模块未打包。
- 本地 Python 3.11.0rc2 上，按配方布局从固定 sdist 临时组装的包目录通过消费者脚本 6/6 组检查，包括导入路径、类型标记、许可证、测试目录排除、版本格式与排序；这是核心范围调整前的主机包布局模拟，不是 Conan 真包、上游完整测试、目标机验证或官方 CI。

## 配方与验证

配方只复制核心 Python 模块、`py.typed` 和 MIT 许可证，通过 Conan run environment 暴露 `PYTHONPATH`。构建步骤以目标 `python3 -m compileall -q src/incremental` 对固定 sdist 的全部上游模块作语法预检，包含未纳入当前包的集成模块；该命令不代表这些模块已作为 Conan 产物交付或经过消费者验证。`INCREMENTAL_SOURCE_ARCHIVE` 只接受与 conandata SHA-256 一致的本地固定 sdist；否则使用官方源 URL。

消费者测试检查包来源、版本元数据、公开版本字符串、预发布/后发布格式、版本排序和 `getVersionString`。可选 `scripts` extra 依赖 Click，本 Conan 包只覆盖核心 Python 库，不声称包含可选命令行依赖。

## H1 结果（2026-09-28）

- #002 的旧候选在目标机 W3 `build_and_test.sh` 返回 0：Conan create、Python compileall 和包消费者 6/6 通过。该结果绑定 #002 旧候选，不替代当前核心 API 包范围的 W3。
- #002 的 `finish` 返回 1。G1 静态检查要求 `export_sources()` 和 `apply_conandata_patches()`；配方已按仓库 Conan 模式补齐无补丁调用，没有创建空补丁或源码补丁。
- #003 对之前四模块包范围运行官方 `conan-verify`，rc 0，报告 G1/G2 PASS；目标机真实 Conan create、compileall 和旧消费者 6/6。G4 虽标 PASS，但报告未找到 package ID；L2/L4/L5 因无 cache 路径跳过。#003 没有运行 W3、finish 或上游 Trial，不能外推至当前核心范围。
- #002 的 `finish` G0 因缺少 `.build-context` 中的 `BUILD_TARBALL` 关联失败，`clean_verify` 随后假设 `configure/make/install`，而该纯 Python sdist 没有 `configure`。Conan Verify 的 G0 是知识图谱预查询，不等于 finish clean-build G0。保留原失败；不记 PASS，也不伪造构建脚本。
- H1 #004 对固定 AF3B 七文件补丁（15,152 B，SHA-256 `af3b3f3c1c23f849194247fbb70e876590f716fab1e8b7a7a9cc945415353154`）执行一次 `setup.sh` 与完整 W3，均 rc 0。真实 Conan create 包 ID 为 `da39a3ee5e6b4b0d3255bfef95601890afd80709`，核心消费者 6/6 组、15 个显式断言通过；包仅包含核心 Version API、类型标记和许可证。目标机 compileall 扫描固定 sdist 源码，不表示 CLI/Hatch 模块被打包。直接 W3 未生成 `.ci-result.json`，不是官方 PR CI。
- H1 #004 的 `tox -e tests` 在 tox-wheel 的 `pip wheel . --no-deps --use-pep517` 顶层 wheel 构建阶段停止，Tox/runner rc 1；`trial incremental` 和 `trial tests/test_examples.py` 均未启动。固定 sdist 的 94 个上游方法通过率不可计算，其中当前核心范围 52 个 Version API 方法也未运行。消费者 6/6、compileall 和 W3 均不能替代上游 Trial。
- 本次记录修订只更新本 `notes.md`；没有改 Conan 配方、manifest 或消费者。H1 #004 执行的是修订前 AF3B 完整补丁；新候选补丁会因本文件变化而得到新摘要，不能称新摘要的补丁字节已在 H1 执行。此次仅文档变化，不重跑 W3。
- 原始 Trial 后快照列出 runner PID `9298`；同 UID 于 2026-09-28 00:22:55 UTC 回读 `/proc/9298` 已不存在。该回读只证明当时 PID 已消失，不推断具体退出时间或方式。未发送信号或重播 Trial。
- H1 对 Trial #005 的只读依赖核验已完成，回执 `evidence/incremental-h1-004/TRIAL-DEPS-005-RESULT.md`（3,355 B，SHA-256 `14c3f584a65b4c871bd63d8e0aa3cfc2f9027c129ccebd475fd2fc529a306ad7`）。在该账号私有根内核过的两个 venv、私有 cache/wheel 文件未发现 Twisted/Trial，`.tox/tests` 不存在；结论只覆盖该私有根，不外推到 H1 全局或其他账号。此次仅只读，无安装、网络获取、Trial/tox/Conan/W3 运行。若后续执行核心 Trial，先固定最小离线 Twisted 依赖闭包、来源、目标 wheel tag 与逐件 SHA-256，交二级审核并另行排队；不安装完整 `requirements_tests.txt`、不改测试、不重跑 W3。
