# jsoncons 1.9.0 — Bootstrap 笔记（pc3-43）

## 来源核验（bootstrap 阶段，官方资料确认）
- 官方仓库：https://github.com/danielaparker/jsoncons
- 正式标签：`v1.9.0` → commit `bcb44594c50c495ee1e690602cdd71455942ad0e`（git ls-remote --tags 实测）
- 许可证：BSL-1.0（LICENSE 文件，Copyright 2013-2020 Daniel Parker）
- 源码 tarball：`https://github.com/danielaparker/jsoncons/archive/refs/tags/v1.9.0.tar.gz`
- SHA-256：`f1017b36e4e034acd5c0f5f616bacf5d7a161d6d3a43ff9ddb73fd8dca4d3cd9`（tarball 实测）

## 版本标识核验
- `include/jsoncons/config/version.hpp`：`JSONCONS_VERSION_MAJOR 1` / `MINOR 9` / `PATCH 0`
- CMakeLists.txt：`project(jsoncons CXX)`，`add_library(jsoncons INTERFACE)`，install
  `NAMESPACE jsoncons::` → 消费者 cmake target `jsoncons::jsoncons`，cmake_file_name `jsoncons`

## 结构
- 纯 header-only：`include/jsoncons/`（basic_json.hpp、decode_json.hpp、encode_json.hpp 等）+ `include/jsoncons_fwd.hpp`
- CMake INTERFACE 库（无需编译），JSONCONS_INCLUDE_DIR 安装头文件
- 上游测试：`src/tests/`（自研单元测试框架）；工具 `src/examples/`
- 依赖：无任何第三方运行依赖（仅标准库）

## 首轮 Adapt / 本地验证
- 待执行：clang++ 编译 test_package smoke test + 上游测试编译运行

## 依赖结论（R02）
- jsoncons 1.9.0 纯 header-only，**无任何第三方运行依赖**（仅标准库；可选 jsoncons_ext 各扩展模块同为库内头文件）。
- L0i 检查对象：jsoncons 自身无 recipe 第三方依赖可解析，不存在"当前库消费自己"或依赖未发布阻塞；本轮依赖可用性门禁不适用。

## 配方结构完整性（R02，L0a-L0e）
- conanfile.py / conandata.yml / manifest.yaml / notes.md / test_package/{CMakeLists.txt, conanfile.py, MANIFEST.yml, test_jsoncons.cpp} 全部存在。
- conanfile.package() 已修正：复制 include/jsoncons/ + include/jsoncons_ext/（R01 曾误写 jsoncons_fwd.hpp，1.9.0 实际无该顶层文件）。
---

**编译结束**: 2026-08-31 09:08
**最终状态**: built
