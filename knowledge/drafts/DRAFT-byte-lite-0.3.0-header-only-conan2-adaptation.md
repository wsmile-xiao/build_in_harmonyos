# DRAFT-byte-lite-0.3.0-header-only-conan2-adaptation

martinmoene/nonstd-lite 系单文件 header-only 库：上游 Conan 1.x 配方迁移 Conan 2.x
+ CMake INTERFACE 消费验证 + 上游测试入口恢复（OHOS aarch64）
Conan 2.29.1 + OHOS aarch64 + clang 15

- **ID**: DRAFT-byte-lite-0.3.0-header-only-conan2-adaptation
- **触发工具**: conan, cmake, conan-create, conan-verify, test_package
- **阶段**: packaging, configuration, testing, verification
- **严重度**: 🟡 warning (2)
- **分类**: conan, cmake, header-only, packaging, ohos

---

## 问题（Problem）

byte-lite 0.3.0（`https://github.com/martinmoene/byte-lite`，GitHub 重定向至
`nonstd-lite/byte-lite`）是 std::byte 的 C++98/11/14/17 单文件 header-only 回移库
（BSL-1.0）。上游仓库自带 **Conan 1.x 配方**：

```python
from conans import ConanFile, CMake
class ByteLiteConan(ConanFile):
    def build(self): pass
    def package(self):
        cmake = CMake(self)
        cmake.definitions["BYTE_LITE_OPT_BUILD_TESTS"] = "OFF"
        cmake.configure(); cmake.install()
    def package_info(self): self.info.header_only()
```

在 Conan 2.x（本项目基线 2.29.1）下该配方无法直接复用：`from conans import ...`
已移除（No module named conans）、CMake helper 调用风格不同、无 `package_type`
声明、`self.info.header_only()` 为 Conan 1 遗留 API。本项目所有 lite 系库（any-lite
等）均需按 Conan 2.x 重写才能通过 conan create/conan-verify 并供下游
`find_package(byte-lite)` 解析到 INTERFACE target `nonstd::byte-lite`。

**错误特征**：`No module named conans` | `from conans import` 语法错误 |
`find_package(byte-lite)` 找不到 target | header-only 库 install 无产物 |
上游 CTest 测试入口缺失（无法验证 cpp98/11/14/17 可编译）。

---

## 根因（Root Cause）

martinmoene/nonstd-lite 系库是单文件 header-only（`include/nonstd/byte.hpp`），
CMake 以 INTERFACE library 暴露（目标 `nonstd::byte-lite`、包 `byte-lite`，
`BYTE_LITE_OPT_BUILD_TESTS/EXAMPLES` 选项控制上游测试入口），版本号仅由 git tag
表达（头文件无版本宏）。上游仍携带 Conan 1.x 配方，Conan 2.x 下 API 不兼容，
必须整体重写；同时需显式声明 `package_type=header-library`、`cmake_layout`、
`CMakeToolchain`、`cpp_info.set_property("cmake_file_name"/"cmake_target_name")`
才能让 CMakeDeps 生成下游可 `find_package` 的 CONFIG 并解析 INTERFACE target。

**影响范围**：martinmoene/nonstd-lite 全系单文件 header-only 库（byte-lite、
any-lite、optional-lite、span-lite、expected-lite、variant-lite 等）首次
OHOS/arm64 Conan 2.x 配方编写；任何上游仍带 Conan 1.x conanfile.py 的
header-only 库迁移；依赖 CMake INTERFACE target 消费的 test_package 编写。

---

## 方案（Solution）

Conan 2.x header-only lite 迁移骨架（本归档已实现，`archives/b/byte-lite/0.3.0/`）：

1. **conanfile.py**（Conan 2 风格重写）：
   - `from conan import ConanFile`；`from conan.tools.files import get, apply_conandata_patches, export_conandata_patches`；`from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout`
   - `package_type = "header-library"`；`settings = "os", "compiler", "build_type", "arch"`
   - `layout()` → `cmake_layout(self)`
   - `export_sources()` → `export_conandata_patches(self)`
   - `source()` → `get(self, **self.conan_data["sources"], strip_root=True)` + `apply_conandata_patches(self)`
   - `generate()` → `CMakeToolchain`；OHOS 映射：`if self.settings.os in ("Linux", "OHOS"): tc.cache_variables["CMAKE_SYSTEM_NAME"]="Linux"; tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"]="aarch64"`；打开 `BYTE_LITE_OPT_BUILD_TESTS=True`、`BYTE_LITE_OPT_BUILD_EXAMPLES=False` 恢复上游测试入口
   - `build()` → `cmake.configure(); cmake.build(); cmake.test()`
   - `package()` → `cmake.install()`
   - `package_info()` → `cpp_info.set_property("cmake_file_name", "byte-lite")`；`cpp_info.set_property("cmake_target_name", "nonstd::byte-lite")`；`cpp_info.libs = []`
2. **test_package/**：`conanfile.py` 用 `generators = "CMakeDeps"`、`requirements()` 引用被测包；`CMakeLists.txt` 用 `find_package(byte-lite REQUIRED)` 链接 `nonstd::byte-lite`；`test_byte_lite.cpp` 实际调用被测 API（`nonstd::byte` 构造、`to_integer`、位运算 `| &`、比较）。**test() 必须实质调用被测包 API**（R34），不得只打印字符串。
3. **conandata.yml**：`sources.url` 指向官方 release tarball
   `https://github.com/martinmoene/byte-lite/archive/refs/tags/v0.3.0.tar.gz`，`sha256`
   实测填写（`1a19e237b12bb098297232b0a74ec08c18ac07ac5ac6e659c1d5d8a4ed0e4813`）。
4. **test_package/MANIFEST.yml**（conan-verify G1 / CI L0e 要求）：声明上游测试
   `upstream_test_in_build: true`、`upstream_test_command: "ctest --output-on-failure"`、
   4 个 CTest 入口（test-cpp98/11/14/17）与 test_package 消费者测试。
5. **上游测试入口恢复**：CMake 选项 `BYTE_LITE_OPT_BUILD_TESTS=ON` 时生成 4 个 CTest
   可执行（`test-cpp98/11/14/17`），本地 `ctest --test-dir build` 4/4 全过即证明头文件
   在 C++98~17 各标准下均可编译。

---

## 验证（Verification）

- `python3 scripts/ohc-run.py conan-verify byte-lite 0.3.0 --profile ohos-aarch64 --project-dir <worktree>`：G0-G4 + L2/L4/L5 全过（exit 0，可标记 published）
- `conan create archives/b/byte-lite/0.3.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`：test_package 输出 `PASS: byte-lite header-only 库链接和核心 API 验证通过`（exit 0）
- `conan test archives/b/byte-lite/0.3.0/test_package byte-lite/0.3.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`：exit 0
- 上游测试：`cmake -S . -B build -DBYTE_LITE_OPT_BUILD_TESTS=ON -DBYTE_LITE_OPT_BUILD_EXAMPLES=OFF && cmake --build build && ctest --test-dir build` → `100% tests passed, 0 tests failed out of 4`（test-cpp98/11/14/17）

---

## 适用边界（Scope）与查重差异（Dedup）

**适用**：martinmoene/nonstd-lite 系单文件头库的 Conan 2.x 首配方；上游带 Conan 1.x
配方的 header-only 库；需暴露 CMake INTERFACE target 供下游消费并恢复上游测试入口的场景。
**不适用**：非 header-only 库（需编译产物）；无上游 CMake 的库；纯聚合元包。

**查重差异**：`DRAFT-protozero-1.8.2-headeronly-consumer` 仅覆盖 header-only 库的
CMake 消费边界与 NDEBUG getter 陷阱（未涉及 Conan 1.x→2.x 迁移、INTERFACE target 暴露、
上游 CTest 恢复）；`DRAFT-conan-staticlib-transitive-headers` / `DRAFT-conan-copy-keep-path-nesting`
属 Conan copy/传递头语义；`DRAFT-ohos-requirements-only-metapackage` 属聚合元包。
`knowledge/graph`、`knowledge/doc`、`knowledge/drafts` 均无 any-lite/byte-lite/martinmoene
条目。本条目新增价值：上游 Conan 1.x 配方在 Conan 2.x 下不可直接复用、需完整重写的
确定性迁移骨架 + INTERFACE target 消费验证 + 上游 CTest 4 入口恢复，属可复用 L2 经验。

---

## 首错与恢复条件（First Error / Recovery）

R02 finish Step5/10 W3 本地 CI 在 full 整仓扫描（45336 文件）下被**其他库**历史已跟踪
垃圾文件拦截：`archives/g/goaccess/1.10.2/ncurses-headers.tar.gz`、
`archives/s/scudo-malloc/19.1.6/.manifest-complete`、`.progress-closed`（均在
origin/main 中被跟踪、由其他库适配提交引入，不在本任务允许范围
`archives/b/byte-lite/**` 内）。属无关历史基线外部阻塞，与 byte-lite 本库无关。
已执行 W1 基线同步（ff origin/main → 076a04938c）并清理本库 E017 临时残留
（`conandata.yml.ghfast-bak` 已逐字节恢复）。恢复条件：本地 W3 需在真实 CI 的
PR-diff 作用域下复核（CI 不整仓扫描），或分析端确认基线垃圾清理后再跑 W3/finish。
