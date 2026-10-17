# DRAFT-concurrencpp-0.1.7-cmake-header-install-subdir

> Contributor: pc1-12 | Status: Draft | Updated: 2026-09-02
> Source: concurrencpp 0.1.7 HarmonyOS PC 适配（PR #7620，conan-verify G2 失败链）
> 领域：CMake + Conan 配方（test_package 消费者头文件解析）

## 背景

concurrencpp 0.1.7 是 C++20 并发库（executors/results/coroutines/timers），CMake 构建。
在 HarmonyOS PC（aarch64-linux-ohos，OHOS armv8）上做 Conan 适配时，`conan create`
在 **test_package 阶段**失败：消费者 `#include <concurrencpp/concurrencpp.h>` 找不到头文件。
修复 `conanfile.py` 的 `package_info()` 后 conan-verify G2 全门禁通过。

## 错误签名

```text
test_package/test.cpp:4:10: fatal error: 'concurrencpp/concurrencpp.h' file not found
ERROR: concurrencpp/0.1.7@ohpcd/stable (test package): Error in build() method
```

## 根因

上游 `CMakeLists.txt` 把公共头安装到 **版本化子目录**：

```cmake
set(concurrencpp_include_directory "${CMAKE_INSTALL_INCLUDEDIR}/${concurrencpp_directory}")  # include/concurrencpp-0.1.7
install(DIRECTORY "${PROJECT_SOURCE_DIR}/include/" DESTINATION "${concurrencpp_include_directory}")
```

且 `target_include_directories` 只用 `$<BUILD_INTERFACE:...>` 包裹、未声明
`$<INSTALL_INTERFACE:...>`，导出的 CMake target 不携带安装 include 路径。
conan 模板配方的 `package_info()` 默认 `cpp_info.includedirs=["include"]`，与
实际安装位置 `include/concurrencpp-0.1.7/` 不匹配 → 消费者 find_package 后
include 路径解析失败，test_package 找不到头文件。

## 触发条件

- 上游 CMake 将公共头安装至 `include/<subdir>`（常为 `include/<lib>-<version>/`）
- 消费者测试以 `#include <lib/...>` 形式引用（前缀即子目录）
- 配方 `package_info()` 未同步声明实际 includedirs

## 修复方案

`conanfile.py` 的 `package_info()` 显式声明 includedirs 指向实际子目录：

```python
def package_info(self):
    self.cpp_info.libs = ["concurrencpp"]
    self.cpp_info.includedirs = ["include/concurrencpp-0.1.7"]   # 匹配上游 install 目标
    self.cpp_info.set_property("cmake_file_name", "concurrencpp")
    self.cpp_info.set_property("cmake_target_name", "concurrencpp::concurrencpp")
```

同时把 test_package 的 `test()` 改为 `self.run(...)` 直接执行消费者二进制（满足 L0d）。

## 验证（R02 复验）

- `conan create`（ohos-aarch64 profile）通过，G0-G4 + L2/L4/L5 全门禁 PASS
- HarmonyOS 专项测试（`harmonyos_concurrency_test.cpp`，runtime/thread_executor/
  lazy_result 协程）编译运行 PASS：`parallel sum=36 unique_threads=8 coroutine_sum=42`
- 上游测试全量通过率 150/150 = 100%
- 证据日志（含 SHA-256）：
  - `~/ohpcd-evidence/concurrencpp-0.1.7/special_test_audit.log`
  - `~/ohpcd-evidence/concurrencpp-0.1.7/local_gate_revalidation.log`
  - `~/ohpcd-evidence/concurrencpp-0.1.7/upstream_test_ledger.log`

## 适用范围

所有 CMake 工程把公共头安装到 `include/<subdir>`（如 `include/libairspyhf`、
`include/libusb-1.0`、`include/<lib>-<version>`）且消费者 `#include <lib/...>`
的场景；只要上游 INSTALL_INTERFACE 未导出安装 include 路径、或导出子目录与
模板 includedirs 不一致，都适用本方案。

## 反例（不适用情形）

- 上游把头平铺安装到 `include/` 根（`install(DIRECTORY include/ DESTINATION include)`），
  模板默认 includedirs 已正确 → 无需改 includedirs
- header-only 库无编译产物、消费者仅 include → 不涉及 libs，但仍需 includedirs 匹配

## 恢复条件

若撤销 `package_info.includedirs` 修改，test_package 将再次报
`fatal error: 'concurrencpp/concurrencpp.h' file not found`，G2 门禁回退失败。
