# outcome

Outcome — a C++17/20 error handling library (result/outcome types with
configurable NoValuePolicy) by Niall Douglas. Header-only.

- 官方仓库：https://github.com/ned14/outcome
- 许可证：Apache-2.0 OR CC-BY-4.0（双许可任选，Licence.txt）
- 版本：2.2.9（标签 `v2.2.9`，commit `571f9c930e672950e99d5d30f743603aaaf8014c`）
- 目录结构：`archives/o/outcome/{version}/`（conanfile.py + conandata.yml + test_package/ + manifest.yaml + notes.md）
- 说明：打包 tarball 内自包含的 single-header 版本（outcome.hpp/outcome-basic.hpp/outcome-experimental.hpp）；include/ 模块版依赖 quickcpplib/status-code 子模块（tarball 不分发、制品仓未发布），上游 Catch2 测试套件因此不可运行（notes.md 如实申报）
