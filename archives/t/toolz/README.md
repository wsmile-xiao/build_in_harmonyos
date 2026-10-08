# toolz

toolz 提供迭代器、函数和字典操作的 Python 函数式工具。上游版本 1.1.0 是纯 Python 包，运行时只依赖 Python 标准库；配方将 `toolz` 与兼容别名 `tlz` 安装到 Conan 包的 `lib/python`，并通过 `PYTHONPATH` 提供导入路径。

上游项目：https://github.com/pytoolz/toolz

许可证：BSD-3-Clause。

2026-10-01，在 OpenHarmony PC aarch64、Python 3.12.9、OHOS 适配 Conan 2.29.1 上，真实 Conan create/test_package 与完整本地 W3 通过；原始上游 pytest 186/186，消费者5/5组、12/12断言，且 toolz/tlz 均来自本次 Conan 包。源码和配方没有补丁。

Toolz 为纯 Python 包，没有原生编译/链接或 bin/ 产物；W3 的 L2 原值为 skip: no bin/ dir。本地构建状态为 built，尚未上传；目标验证不代表官方 CI、评审、合入或计分完成。详细来源、验证命令和限制见版本目录 notes.md。
