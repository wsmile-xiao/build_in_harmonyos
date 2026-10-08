# toolz 1.1.0 适配笔记

## 来源与配方

- 原始 PyPI toolz-1.1.0.tar.gz，52,613 bytes，SHA-256 `27a5c770d068c110d9ed9323f24f1543e83b2f300a687b7891c1a6d56b697b5b`。
- 纯 Python 运行时包，依赖 Python 标准库，无 C/C++ 编译/链接，无源码补丁。
- Conan `package_type = "unknown"`，将 toolz/tlz 源码复制到 lib/python、复制 LICENSE.txt，并设置 PYTHONPATH。

## 2026-10-01 目标验证

- OpenHarmony PC aarch64；UID20020084；Python3.12.9，OHOS 适配 Conan2.29.1；官方 ohos-aarch64 host/build profile。
- 官方框架提交 `255e5069639b3be244f4988c966a5120bd5608f2`。单次官方 FinishPipeline.step35_local_ci() 执行完整 setup.sh/build_and_test.sh，W3 RC0、setup/build RC0、prdiff选8文件、JC_ERRORS=0；没有执行全量finish。
- W3内真实 Conan create 与 test_package 通过，消费者5/5组、12/12断言，包含 toolz/tlz 来源均在本次 Conan package_folder/lib/python 的断言。
- Conan完整引用：`toolz/1.1.0#a6e76247ec603d163282b90d3596a8c5:da39a3ee5e6b4b0d3255bfef95601890afd80709#179a1f9edd802f92385ce02f5272c28d`。
- 原始源包解包后，在源码根执行 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -B -m pytest -q --junitxml=upstream-junit.xml`，pytest9.0.2与依赖仅解包至私有PYTHONPATH；RC0，186 passed，JUnit186/失败0/错误0/跳过0。44源码文件前后不变；五组消费者不重复计入上游186项。
- 官方自然生成W3日志SHA-256 `8d2f30ccecd7d391d5fbcea9b783f58424751048ab2bacb15353c3fc8dc2fb3d`；原始回收归档SHA-256 `f6bbea1d0a85668e368796fdf66e109b9cf5e1affda771836aa783df0dff84fa`。

## 限制与原始失败

- W3 L2为 `skip: no bin/ dir`，不能称原生运行/链接通过；L0/L1通过，L4为无patches，L5为lib/含内容。
- W3预下载有失败告警，随后Conan从固定files.pythonhosted.org URL正确下载并按配方SHA验证；未声称Conan直接使用另存的输入副本。首轮历史preflight在PF0裸Git子进程启动失败，未进入Conan；本次没有重放旧诊断、shim或preflight。
- 状态 built、真实日期2026-10-01；未upload，不写published。本地W3不代替官方CI/AI或正式评审。
- 平台任务lang=cpp，上游实际为Python，标签保持不变，不承诺资格/计分。
- 归档规范必需的软件级README/manifest与PF9深度检查冲突，保留文件原位和实际FAIL；按准确两路径内部例外处理，公开PR披露替代创建入口的完整跳过范围。
