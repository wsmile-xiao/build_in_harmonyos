# libosmpbf 1.6.1 — 适配笔记

> 档案创建时间: 2026-09-15
> 状态: built（待真机预检，未提交）
> 申请人: momimgya / 队伍: 干

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | libosmpbf |
| 版本 | 1.6.1 |
| 上游仓库 | https://github.com/openstreetmap/OSM-binary |
| 源码包 | https://github.com/openstreetmap/OSM-binary/archive/refs/tags/v1.6.1.tar.gz |
| sha256 | 54e0f234ace310a4256dc7d4fc707837f532a509cc3ef2940dacbdc4ebd9ce15（与 Homebrew osm-pbf 公式一致） |
| 构建系统 | CMake（顶层 CMakeLists + osmpbf/ + tools/） |
| 许可证 | LGPL-3.0-or-later（.proto 与 osmpbf.h 为 MIT） |

## 二、上游结构审计

- 顶层 `CMakeLists.txt`（v1.6.1）：`cmake_minimum_required(VERSION 3.10)`，
  `project(osmpbf VERSION 1.5.0)`，`find_package(Protobuf REQUIRED)`，
  `add_subdirectory(osmpbf)` + 非 MSVC 时 `add_subdirectory(tools)`。
- `osmpbf/CMakeLists.txt`：`protobuf_generate_cpp(fileformat.proto osmformat.proto)`，
  构建 `osmpbf`（STATIC）与 `osmpbf_shared`（SHARED，OUTPUT_NAME osmpbf），
  `target_compile_features(... cxx_std_11)`，链接 `protobuf::libprotobuf`，
  安装静态库/动态库与三头文件（osmpbf.h + 生成的 fileformat.pb.h/osmformat.pb.h）。
- `tools/CMakeLists.txt`：`find_package(ZLIB REQUIRED)` + `find_package(Threads)`，
  构建演示工具 `osmpbf-outline` 并安装到 bin（含 man 页）。
- **C++ 测试：无。** 全源码树无 `enable_testing()` / `add_test()` /
  `add_custom_target(check)`，无 `tests/` 或 `test/` 目录，无 `make check` /
  `ctest` 入口。唯一的 `ReadFileTest.java` 是 Java 侧 Maven 测试，
  与本 C++ Conan 包无关（见 test_package/MANIFEST.yml 审计）。
- 结论：`upstream_tests_exist: false`，以 `status: no_tests` 诚实上报，
  不伪造通过率（c10t / bankstown-lv2 先例）。

## 三、依赖选型

| 依赖 | 版本 | 理由 |
|------|------|------|
| protobuf | 33.6 | 制品仓现行标准（grpc 1.70.0 / brpc 1.17.0 / etcd-cpp-apiv3 同款），transitive_headers+transitive_libs |
| zlib | 1.3.1 | tools 侧 `find_package(ZLIB)` 所需；与 protobuf 33.6 无版本冲突（etcd 先例） |

- abseil-cpp 为 protobuf 的传递依赖，不直接 require，
  仅在 generate 阶段取其 `absl_DIR`（缺失则警告跳过）。

## 四、OHOS 适配点

1. **CMAKE_SYSTEM_NAME=Linux（OHOS 时）**：device cmake 无 HarmonyOS 平台模块，
   E092 / barrier / brpc 先例，强制走上游 Linux 分支。
2. **protobuf CONFIG 接线**：制品仓 protobuf 导出 `cmake_find_mode=none`，
   显式注入 `Protobuf_DIR` / `utf8_range_DIR` / `absl_DIR`，
   并固定 `Protobuf_PROTOC_EXECUTABLE` 与 `PROTOBUF_PROTOC_EXECUTABLE`
   为 `<protobuf>/bin/protoc`（grpc / brpc 接线方式）。
3. **C++ 标准**：profile 已定 C++17；配方另以 `check_min_cppstd(17)` 校验，
   覆盖 protobuf 33.x 经 abseil 引入的 C++17 需求（上游 issue #76 背景）。
4. **动静二选一**：上游恒产 static + shared，
   package 阶段按 `shared` 选项保留一种（libbpf 先例）。
5. **无补丁**：`protobuf_MODULE_COMPATIBLE` 与
   `CMAKE_FIND_PACKAGE_PREFER_CONFIG` 均已由上游顶层 CMake 设置，
   无需改动源码。

## 五、test_package 设计（R34）

- `test.cpp`：7 项真实 API 断言——版本宏非空、三常量取值、
  BlobHeader 序列化往返、Blob 字段往返、PrimitiveBlock stringtable 往返、
  HeaderBlock bbox/特性往返；全部失败即非零退出。
- `conanfile.py`：CMake 构建消费者，运行二进制成功后输出
  `HMBS_TEST_PACKAGE_RESULT`（discovered=7/passedCount=7），
  并同步输出 `HMBS_UPSTREAM_TEST_RESULT`（status=no_tests，
  discovered/executed/passed/failed=0，附审计 reason）。
- `osmpbf-outline` 随包安装到 bin，但包保持纯 library 类型，
  不声明 bindirs（L0k 不触发，R38 合规）。

## 六、验证命令（真机预检执行）

```bash
conan create archives/l/libosmpbf/1.6.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

- 预期：conan create 成功，test_package 7/7 通过，
  上游标记为 no_tests（0/0，非失败）。
- 本轮工作树未提交，真机预检由 HMBS 后台统一执行后回填 PR 正文数字。

## 七、风险与限制

- 上游 `project(VERSION 1.5.0)` 滞后于 tag 1.6.1（1.6.x 仅改 Java 侧），
  生成的 SOVERSION 为 1；属上游现状，不做改动。
- `osmpbf-outline` 为演示工具，未纳入 test_package 执行覆盖；
  库 API 已全覆盖。
