# gsettings-qt 1.1.1 — Qt6/QML 工程在 conan 依赖包下的工具与 QML 模块发现链

- **软件/版本**：gsettings-qt 1.1.1（CMake + Qt6 + cmake-extras QmlPlugins）
- **日期**：2026-09-15
- **触发**：本地 `conan create`（与 CI 同参数）在第 1–3 次失败后修复通过
- **草稿条目**：`knowledge/drafts/DRAFT-gsettings-qt-qml-toolchain.kv`

## 错误签名

```
Could not find QML_PLUGIN_DUMP using the following names: qmlplugindump
Could not locate qmlplugindump.                       # cmake-extras QmlPluginsConfig.cmake
Type TestCase unavailable
module "QtQuick.Window" is not installed
The directory '<X>' does not contain any test files matching 'tst_*.qml'
The direct dependency 'cmake-extras' is not used by any '(cpp_info/components).requires'
```

## 根因（三类发现点，均非"依赖缺失"）

1. **构建期工具不在 PATH**：上游 `GSettings/CMakeLists.txt` 在 configure 阶段执行
   `find_program(QML_PLUGIN_DUMP qmlplugindump REQUIRED PATHS /usr/lib/qt6/bin ...)`；
   cmake-extras 的 `QmlPluginsConfig.cmake` 在 `find_package(QmlPlugins)` 时还会再查一次，
   失败即 `FATAL_ERROR "Could not locate qmlplugindump."`。
   conan 的 host requires 包目录（qtdeclarative 包 `bin/qmlplugindump`）默认不进 PATH。
   该工具是 OHOS arm64 本机可执行文件，运行时还需 `LD_LIBRARY_PATH` 指向 qtbase/qtdeclarative 的 `lib/`。

2. **QML 导入路径被测试属性覆盖**：上游 `set_tests_properties(qmltest PROPERTIES ENVIRONMENT
   "QML2_IMPORT_PATH=${CMAKE_BINARY_DIR};...")` 覆盖进程环境，导致 QtTest/TestCase.qml 需要的
   `QtQuick.Window` 等模块（位于 qtdeclarative 包 `qml/`）不可见。
   Qt6 同时读取 `QML_IMPORT_PATH`，该变量不被测试属性覆盖 → 用它补充即可，无需改上游。

3. **测试工作目录**：QuickTest 驱动按 cwd 查找 `tst_*.qml`；ctest 在 `add_test` 所在目录执行（通过），
   手工在别处运行同一可执行文件会报找不到测试文件（调试时的假失败）。

4. **cmake-extras 的依赖声明形态**：作为 host `requires` 会触发 conan
   `direct dependency ... not used by any (cpp_info/components).requires` → 应为 `tool_requires`。

## 推荐方案（env-injection，不改上游）

```python
# generate() 内
env = Environment()
for pkg in ("qtbase", "qtdeclarative", "glib", "qtshadertools"):
    prefix = self.dependencies[pkg].package_folder
    env.prepend_path("PATH", os.path.join(prefix, "bin"))
    env.prepend_path("LD_LIBRARY_PATH", os.path.join(prefix, "lib"))
for pkg in ("qtdeclarative", "qtbase", "qtshadertools"):
    env.prepend_path("QML_IMPORT_PATH", os.path.join(self.dependencies[pkg].package_folder, "qml"))
env.vars(self).save_script("conanbuild_<pkg>_env")
```

配套：`self.tool_requires("cmake-extras/1.9")`（构建期 CMake 模块，不进消费者依赖链），
`generate()` 内用 `self.dependencies.build["cmake-extras"].package_folder` 注入 `CMAKE_PREFIX_PATH`；
qtbase 进 `CMAKE_PREFIX_PATH`，qtdeclarative/qtshadertools 进 `QT_ADDITIONAL_PACKAGES_PREFIX_PATH`。

## 验证

```
conan create archives/g/gsettings-qt/1.1.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=<同> \
  --build=missing --build="gsettings-qt/*"
# → 上游 ctest: 100% tests passed, 0 tests failed out of 2（cpptest 7 项 / qmltest 9 项）
# → test_package: 13 项断言全部 PASS
```

## 禁止项

- 禁止把 cmake-extras（或同类 CMake 模块数据包）声明为 host requires。
- 禁止为绕开 QML 导入路径问题去打上游 `tests/CMakeLists.txt` 补丁（QML2_IMPORT_PATH 会被覆盖，
  补丁无效；且违背"优先配方侧解决"）。
