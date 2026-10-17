# socksio

[socksio 1.0.0](https://pypi.org/project/socksio/1.0.0/) 是纯 Python 的 SOCKS4、SOCKS4A 与 SOCKS5 协议库，许可证为 MIT。配方固定 PyPI sdist 的 SHA-256 `f88beb3da5b5c38b9890469de67d0cb0f9d494b78b106ca1845f96c10b91c4ac`，包内包含 Python 模块、`py.typed` 与原始 `LICENSE`，不需要原生编译或额外运行依赖。

Conan `build()` 使用 Python 标准库 `compileall` 检查源码语法；`test_package` 从真实 Conan 包导入模块，验证 SOCKS4/SOCKS4A/SOCKS5 协议与错误应答。固定源码的上游 pytest 99/99 已在 H1-006 独立运行；H1-007 的 Conan create 与完整 W3 各运行消费者 5/5，未在 `build()` 中重跑上游测试。H1-007 的 G1 和 finish 总门禁仍失败，状态保持待审核。
