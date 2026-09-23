# DRAFT-tinyspline-0.6.0-cmake-libdir64-cmakedeps

## 问题

OHOS aarch64 下用 Conan 2 + CMake 构建三方库时，`conan create` 主包构建成功，但
test_package 的 `find_package`/链接阶段报：

```
CMake Error at .../cmakedeps_macros.cmake:81 (message):
  Library 'tinysplinecxx' not found in package.  If 'tinysplinecxx' is a
  system library, declare it with 'cpp_info.system_libs' property
```

库文件明明在包内（`libtinysplinecxx.a` 存在），CMakeDeps 却在 `lib/` 下找不到。

## 根因

上游 CMake 使用 GNUInstallDirs 时，在 64 位平台上 `CMAKE_INSTALL_LIBDIR` 默认选择
`lib64`（OHOS aarch64 命中 multiarch 规则），于是 `cmake.install()` 把库装进
`lib64/`。而 Conan 默认约定 `lib/`，CMakeDeps 生成的 imported target 在
`libtinysplinecxx.a` 的查找目录（`lib`）中找不到该库，直接报
"not found in package"，阻断 test_package 配置。

`CMakeToolchain` 里写 `tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"` 无效，因为
GNUInstallDirs 读的是 cache 变量，普通 variables 压不过默认值。

## 方案

1. `generate()` 中用 **cache 变量**强制 libdir：

```python
tc.cache_variables["CMAKE_INSTALL_LIBDIR"] = "lib"
```

2. `package_info()` 兜底同时暴露 `lib` 与 `lib64`：

```python
self.cpp_info.libdirs = ["lib", "lib64"]
```

两处同时设置后，CMakeDeps 能定位库文件，test_package 配置/编译/链接/运行全过。

## 验证

- `conan create archives/t/tinyspline/0.6.0 -pr:h=ci/conan/profiles/ohos-aarch64
  -pr:b=... --build=missing --user=ohpcd --channel=stable` → 主包构建成功，
  test_package `1/1 Test #1: test_tinyspline ... Passed`。
- 包内产物核验：`lib/libtinyspline.a`、`lib/libtinysplinecxx.a`（`lib64` 下不再
  有库文件）。
- conan-verify G2/G3/G4 全 PASS。

## 适用边界

- OHOS aarch64（或任何 GNUInstallDirs 默认选 `lib64` 的 64 位平台/工具链）上，
  上游 CMake 未显式固定 `CMAKE_INSTALL_LIBDIR` 的三方库。
- 库类型（package_type = library）且 `package_info` 声明了 `cpp_info.libs`。

## 反例与限制

- 若上游 CMake 显式写死 `LIBDIR lib64` 或使用自定义 install 规则，cache 变量可能
  仍被覆盖，需按上游实际路径设置 `libdirs`。
- 系统同名库（R26）仍需静态化；本条目只解决 libdir 查找，不改变链接策略。
- 纯可执行包（无 lib 产物）不适用，应参考 E221 建模。