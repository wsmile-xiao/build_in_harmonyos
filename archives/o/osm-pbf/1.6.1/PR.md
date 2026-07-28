feat(osm-pbf): 1.6.1 适配 HarmonyOS PC（对齐 Homebrew）

---

## PR 信息

- **三方库名称**：osm-pbf
- **上游版本**：v1.6.1
- **上游仓库地址**：https://github.com/openstreetmap/OSM-binary
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent（CMake 交叉编译；R18 cmd-pkgs；宿主 protoc codegen；R34 test_package）

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试（Java） | 3 | `ReadFileTest`（1）+ `WriteFileTest`（2），JUnit 4 / `mvn package` |
| 单元测试（C++） | 0 | CMake 无 gtest/ctest |
| 冒烟（C++） | 1 | 上游 C CI 与 Homebrew：`osmpbf-outline resources/sample.pbf` |
| **合计** | **4** | 本适配为 C++/CMake，不构建 Java |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试（Java） | 0 | −3（范围外） | 未改上游 Java 测试 |
| 冒烟（C++） | 0（交叉）/ 1（真机待跑） | 用例未改 | 可运行时执行 `osmpbf-outline sample.pbf` |
| 消费者 API（test_package） | 1 | 新增（R34） | `test.cpp`：`#include <osmpbf/osmpbf.h>`，调用 `BlobHeader` set/serialize/parse，**强制链接 libosmpbf**；交叉环境完成 compile/link，跳过 qemu 运行 |
| **合计** | **1**（交叉可自动验证） | +1 API 消费者测试 | 见 `test_package/` |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无适用于 Conan 包消费侧的测试入口，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：新增 R34 合规消费者测试——编译链接并调用 `OSMPBF::BlobHeader` API；可运行时再执行 Homebrew 等价冒烟
> - **补全原因**：上游 C++ 无 gtest；仅有 CI/Homebrew 冒烟。需验证头文件可用、符号可链接，避免「只检查文件存在」的虚假通过
> - **新增测试文件清单**：
>   1. `test_package/test.cpp` — `OSMPBF_VERSION` / 常量 + `BlobHeader` round-trip（链接 libosmpbf）
>   2. `test_package/CMakeLists.txt` — `find_package(osmpbf)` + `Protobuf`
>   3. `test_package/conanfile.py` — `build()` 强制 compile/link；`test()` 可运行时 `ctest` + `osmpbf-outline`
>   4. `test_package/MANIFEST.yml` — 上游/适配测试声明

---

## 验证结果

- 编译状态：通过（OpenHarmony SDK 6.1.0.31 / OHOS Clang 15.0.4，Docker `oh_compile`）
- 上游测试用例通过率：Java 未跑（范围外）；C++ 冒烟交叉未跑（qemu SIGILL），待真机
- 新增测试用例通过率：compile/link 1/1（100%）；`conan test … -pr:h=ohos-aarch64-6.1` 已产出 `test_osmpbf` 可执行文件

### 编译验证

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 编译无错误 | 通过 | `conan create` / 包构建 |
| test_package 链接 | 通过 | 消费者 `test_osmpbf` 链接 `osmpbf::osmpbf` + `protobuf::libprotobuf` |
| 产物存在性 | 通过 | `libosmpbf.a`、`.so*`、头文件、`osmpbf-outline` |
| ELF 格式 | 通过 | ARM aarch64 / musl |
| 运行测试 | 部分 | 交叉跳过 qemu；真机跑 API 测试 + `osmpbf-outline sample.pbf` |

### 依赖

| 依赖 | 版本 | 来源 |
|------|------|------|
| protobuf | 34.1 | cmd-pkgs（消费者/test_package 链接亦需） |
| abseil-cpp | 20260107.1 | cmd-pkgs |
| zlib | 1.3.1 | cmd-pkgs |
| host protoc | 34.1 | 官方 linux-x86_64 zip（codegen） |

### 补丁说明

无上游源码补丁（`patches_applied: []`）。

---

## 补充说明

1. **R34**：`test_package` 不再做 `os.path.isfile` 空壳检查；`build()` 必须成功编译链接调用 API 的 `test.cpp`。
2. **交叉关键点**：宿主 x86_64 protoc 做 codegen；OHOS protoc + qemu 不可用。
3. **复现**：
   ```bash
   export OHOS_SDK_HOME=/opt/ohos-sdk-6.1
   export OHOS_DEPS_PREFIX=/root/ohos-deps   # protobuf/abseil 前缀
   cd archives/o/osm-pbf/1.6.1
   conan create . -pr:h=ohos-aarch64-6.1 -pr:b=default
   ```
