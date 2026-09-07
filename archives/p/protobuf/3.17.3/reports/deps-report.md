# protobuf 3.17.3 依赖分析报告（S2）

## 1. 目标库结论

- 库名 / 版本：protobuf / 3.17.3
- 来源：依赖库（方式二，无需认领）
- 上游 URL：https://github.com/protocolbuffers/protobuf/releases/download/v3.17.3/protobuf-cpp-3.17.3.tar.gz
- 是否已在仓库完成：否。`archives/p/protobuf/` 已有 21.9/21.12/29.6/33.6/33.6.1/34.1，**无 3.17.3**，需新适配。
- ohpcd 制品仓现有版本（`conan list protobuf/* -r=ohpcd` 实测）：`33.6`、`33.6.1`，**无 3.17.3**。属预期，本次需新发布 3.17.3。

## 2. 依赖解析（来源：上游 `cmake/CMakeLists.txt` v3.17.3）

protobuf 3.17.3 为 2021-05 发行版，构建入口在 `cmake/CMakeLists.txt`，C++ 标准 C++11，构建系统 CMake ≥3.1.3。

| 依赖 | 上游引入方式 | 类型 | Conan recipe? | 实测结果 | 结论 |
|------|------------|------|--------------|---------|------|
| pthread（Threads） | `find_package(Threads REQUIRED)` | 系统库 | 系统自带 | OHOS 目标提供 pthread | 可用 |
| zlib | `protobuf_WITH_ZLIB`(默认 ON) → `find_package(ZLIB)` | **可选** | `zlib/1.3.1` | `conan download zlib/1.3.1 -r=ohpcd` 成功，含 OHOS armv8 clang15 libc++17 Release binary | 可用 |
| abseil-cpp | —（v33.6 引入，3.17.3 **无**） | 无关 | 不需要 | 源码中无 absl/abseil 引用 | 不涉及 |
| utf8_range | 仅 v33.6+ 内嵌 | 无关 | 不需要 | 3.17.3 无 | 不涉及 |

仅一条可选外部 Conan 依赖 `zlib/1.3.1`，已实测可下载。**依赖无缺口**。

## 3. R35 反证记录

- `conan download protobuf/3.17.3 -r=ohpcd`：返回 `system acceleration policy not enabled` —— 由 cnb.cool 对**不存在的 ref** 触发（非认证问题），结合 `conan list protobuf/* -r=ohpcd` 确认仅有 33.6/33.6.1，判 **3.17.3 未发布**。
- `conan download zlib/1.3.1 -r=ohpcd`：**成功**，证明 ohpcd 可访问、zlib 依赖可用（该错误并非整体访问受限）。

## 4. 建议顺序与说明

- 依赖全可用 → 进入 S3 构建。
- zlib 为可选依赖，若启用 `with_zlib=True`，需在配方中 `requires("zlib/1.3.1")` 并设置 `ZLIB_ROOT` 指向 zlib package_folder，使上游 `find_package(ZLIB)`（FindZLIB 模块）能命中 Conan 提供的 zlib。
- 源码自带预生成 `.pb.cc`（`src/google/protobuf/*.pb.cc` 共 11 个），交叉编译 `libprotobuf`/`libprotoc` 无需运行 host `protoc`；`protoc` 目标链接 `libprotoc`/`libprotobuf`，生成式为 OHOS aarch64 目标二进制（供下游使用，不在本机执行）。
