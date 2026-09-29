# metashell

C++ 模板元编程交互式 Shell（Interactive C++ template metaprogramming shell）。

- 上游：https://github.com/metashell/metashell
- 版本：5.0.0（tag v5.0.0）
- 构建：CMake，C++17，依赖全部随源码 vendored（boost/googletest/protobuf/rapidjson/yaml-cpp 等）
- 产物：命令行工具 `bin/metashell`（另含内部静态库，仅随包构建，不对外提供）
- Templight 说明：上游 `build.sh` 的 Templight 步骤是独立 LLVM 构建，本配方跳过该步骤；
  主 CMake 通过 `find_package(Templight)` 探测，未找到时仍可构建核心与 wave/internal/clang 引擎。
