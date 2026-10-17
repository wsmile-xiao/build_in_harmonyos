# cpp_info.libs 必须用上游产物的实际名字（OUTPUT_NAME 覆盖了包名）

**草稿条目**（`DRAFT-libint2-2.7.2-cpp-info-libs-must-use-upstream-output-name`）
来源：libint2 2.7.2 Conan 适配（2026-09-13）。

## 现象

Conan 包名是 `libint2`，但安装产物是 `lib/libint2.a`。
若按包名写 `self.cpp_info.libs = ["libint2"]`，消费者侧会得到 `-llibint2`：

```console
ld: unable to find library -llibint2
```

错误只出现在**消费者**链接期（test_package / 下游），本包自己 `conan create` 的 build/package
阶段完全正常 —— 因此很容易到 CI 才发现。

## 根因

上游 `CMakeLists.txt`：

```cmake
add_library(libint2 $<TARGET_OBJECTS:libint2_obj>)
set_target_properties(libint2 PROPERTIES ARCHIVE_OUTPUT_NAME int2)   # ← 产物名被改成 int2
```

于是磁盘上是 `libint2.a`，而"库名"（Conan 侧 `-l` 参数）是 **int2**。
包名（`libint2`）与库名（`int2`）不一致时，cpp_info 必须按**产物**取值。

## 推荐方案

```python
def package_info(self):
    self.cpp_info.libs = ["int2"]                       # ← 上游产物名，不是包名
    self.cpp_info.set_property("cmake_file_name", "libint2")
    self.cpp_info.set_property("cmake_target_name", "libint2::int2")
```

取证方式（不要凭包名猜）：

```console
$ ls <pkg>/lib
libint2.a  pkgconfig  cmake
$ llvm-nm -g <pkg>/lib/libint2.a | head -3      # 确认归档内容与符号
```

## 回退方案

不写 `cpp_info.libs`，让消费者改用上游安装的 CMake config（`find_package(libint2 CONFIG)` +
`Libint2::cxx`）。可行，但 Conan 的默认消费方式（CMakeDeps 生成的 `<pkg>::<target>`）与
pkg-config 契约都会缺库名，属于"把问题推给消费者"。

## 禁忌

**不要**用符号链接/改名造一个与包名同名的库来迁就错误的 `cpp_info.libs`：
那是掩盖，且与上游 `install(EXPORT)` 导出的 target 名、`.pc` 里的 `-l` 值不一致，
换一种消费方式（pkg-config / 上游 config）依然失败。

## 可复用判据

凡上游 CMake 出现 `OUTPUT_NAME` / `ARCHIVE_OUTPUT_NAME` / `LIBRARY_OUTPUT_NAME`，
一律以 `ls <pkg>/lib` 的产物名（去 `lib` 前缀与扩展名）为准写 `cpp_info.libs`；
同时核对上游导出的 CMake target 名，用 `cmake_target_name` 对齐。
