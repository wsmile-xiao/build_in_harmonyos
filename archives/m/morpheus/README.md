# Morpheus

Morpheus is a modeling and simulation environment for multiscale and multicellular systems biology.

## 当前状态

当前已尝试 CLI simulator only 适配，产物目标为 `bin/morpheus`。配方、CMake 补丁、`test_package` 和 `commands.json` 已写入；OHOS 真机 `conan create` 与 `test_package` 已通过，状态记录为 `built`，尚未上传至制品仓。

这不是路径 B 结论。只有在真实 OHOS 构建输出给出不可绕开的错误后，才进入路径 B 并记录具体阻塞点。

## 适配范围

- 启用：CLI simulator `MorpheusSIM`，安装为 `morpheus`。
- 关闭：Qt GUI、Graphviz library backend、OpenMP、上游 static build。
- 测试：执行最小 MorpheusML XML，断言输出包含 `Simulation finished`。

## 前置依赖

- `boost/1.90.0.1`：新增 CMake-built compiled components，提供 `Boost::program_options`、`Boost::filesystem`、`Boost::system`。
- `xtl/0.7.7`、`xsimd/13.2.0`、`xtensor/0.25.0`：按 Morpheus 上游 fallback 版本拆成 Conan 依赖，避免 FetchContent 联网。
- `zlib/1.3.1.1`、`libtiff/4.7.2`：复用现有归档。
- `libjpeg-turbo/3.2.0`、`zstd/1.5.7`、`libwebp/1.6.0`、`xz/5.6.2`：`libtiff` 的 CMake public deps，需在 Morpheus recipe 中直接声明以生成 `TIFFConfig.cmake` 传递 `find_dependency()` 所需的 CMakeDeps config。
- `libxslt/1.1.45.1`：新增带 `xsltproc` 的构建期工具依赖。

## 已知风险

- PR !3459 build #11923 暴露的 `TIFFConfig.cmake` 传递 `find_dependency(libjpeg-turbo)` 缺失问题已在新端口隔离 job 中修复验证。
- PR !3459 build #12149 暴露的 `lld` runtime `libxml2.so.16` 解析污染问题已通过前置 SDK `llvm/lib` 到 OHOS 工具链命令环境修复；新端口隔离 job r3 已完整通过，仍需等待 GitCode CI 对 PR 分支重跑确认。
- L2 通用 `--help/--version` smoke 仍不适配 Morpheus CLI 输出口径，功能 smoke 由 `test_package` 的最小 MorpheusML 模型覆盖。
- 完整 GUI 适配仍不建议作为当前路径 A 目标；它涉及 Qt5 EOL、Qt 插件、WebEngine/WebKit 和图形资源链。

## 参考资料

- Homebrew formula: https://formulae.brew.sh/formula/morpheus
- Homebrew formula source: https://github.com/Homebrew/homebrew-core/blob/master/Formula/m/morpheus.rb
- Upstream repository: https://gitlab.com/morpheus.lab/morpheus
- Upstream download page: https://morpheus.gitlab.io/download/
