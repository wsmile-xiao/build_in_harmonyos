# E620 — CMakeDeps 生成的 Catch2 配置未把包内 `lib/cmake/Catch2` 加入 `CMAKE_MODULE_PATH`，上游 `include(Catch)` 失败

- **来源**: j4-dmenu 3.2 HarmonyOS PC 适配（`conan create` 配置期）
- **状态**: draft（待审，勿自行 promote）
- **关联**: 与「包内根本不含 CTest 集成模块」的 catch2 打包缺陷同征兆但不同根因——本例模块确实存在于包内，缺的是模块搜索路径接线

## 1. 现象

`conan create` 配置阶段，上游 CMakeLists 走完 `find_package(Catch2 ...)` 后立刻失败：

```text
CMake Error at CMakeLists.txt:135 (include):
  include could not find requested file:

    Catch

CMake Error at CMakeLists.txt:136 (catch_discover_tests):
  Unknown CMake command "catch_discover_tests".
```

值得注意：`find_package(Catch2)` 本身**没有**报错，`Catch2::Catch2` 目标可用，
所以第一眼的判断方向（"依赖没被找到 / 没装"）是错的。

## 2. 根因

两层叠加：

1. **CMakeDeps 不接线模块路径**：`Catch2Config.cmake` 只提供 imported target，
   不会把包内 `<包目录>/lib/cmake/Catch2` 追加到 `CMAKE_MODULE_PATH`。
   而 `include(Catch)` 是按**模块搜索路径**查找 `Catch.cmake` 的——顺带说，
   正确写法是 `include(Catch)` 而非 `include(Catch.cmake)`，后者会跳过搜索路径。
2. **变量被空值覆盖**：`Catch2-Target-release.cmake:35` 里有一句

   ```cmake
   set(CMAKE_MODULE_PATH "" ${catch2_BUILD_DIRS_RELEASE})
   ```

   而 `catch2_BUILD_DIRS_RELEASE` 对这个包是**空**的。这句 `set` 直接把
   `CMAKE_MODULE_PATH` 覆盖成空（连 conan 预置的路径也一并抹掉），
   使后续所有 `include(<Module>)` 都失去搜索路径。

   > 这正是该问题容易被误诊为"包打包不完整"的原因：`Catch.cmake` 其实就在
   > 包内 `lib/cmake/Catch2/` 躺着（实测路径
   > `.conan2/p/catch90796d2e32173/p/lib/cmake/Catch2/Catch.cmake`），
   > 只是没人把它告诉 CMake。

## 3. 修法（在 `generate()` 中显式接线）

用**绝对路径**把模块目录写进工具链变量：

```python
def generate(self):
    tc = CMakeToolchain(self)
    if self.options.with_tests:
        catch2_dir = os.path.join(
            self.dependencies["catch2"].package_folder, "lib", "cmake", "Catch2"
        )
        tc.variables["CMAKE_MODULE_PATH"] = catch2_dir.replace("\\", "/")
    tc.generate()
    CMakeDeps(self).generate()
```

要点：

- 必须是**绝对路径**。相对路径无法抵抗上面第 2 点的空值覆盖语义；
- `CMakeToolchain` 写入的变量在 `CMakeDeps` 生成的 `*-Target-*.cmake` **之前**
  被 include，因此显式赋值能压过那两句 `set`；
- 该目录同时含 `CatchAddTests.cmake`，`catch_discover_tests` 注册用例时也要用它，
  所以整个目录加进去即可，不需要逐文件。

### 禁止做法

- ❌ 从网络下载或手写一份 `Catch.cmake` 放进工程——模块本来就在 catch2 包内，
  自造副本会掩盖真实的路径接线问题，并在 catch2 升级时静默失配；
- ❌ 改用 `include(Catch.cmake)` 绕过搜索路径——同名文件在多个依赖目录下的
  场景无法解析，治标且更脆弱。

## 4. 验证证据（j4-dmenu 3.2 实测）

修好后同一份配方 `conan create` 全绿：

```text
100% tests passed, 0 tests failed out of 79
Total Test time (real) =   1.00 sec
```

- 上游 CTest 注册成功并执行 79 个用例：**73 个通过、0 失败**，
  6 个被上游 `SKIP()` 守卫跳过（本机 `/tmp` 只读，见 j4-dmenu `reports/test-report.md`）；
  上游测试源静态计数另有 258 处断言宏；
- 零源码补丁——仅 `generate()` 三行接线，上游 `CMakeLists.txt` 未动。

## 5. 适用面与边界

- **适用**: 任何 `find_package(Catch2 ...)` + `include(Catch)` + `catch_discover_tests`
  的 C++ 工程，只要经 Conan 2.x（CMakeDeps/CMakeToolchain）落地；
  Catch2 的 CTest 模块装在包内 `lib/cmake/Catch2/` 即命中，与 Catch2 大版本无关。
- **不适用**: 模块装在系统 CMake 模块路径（`/usr/share/cmake*/Modules`）的场景——
  那种情况下 `CMAKE_MODULE_PATH` 被清空也不影响 `include(Catch)`；
  以及直接 `FetchContent` 拉 Catch2 源码的工程（源码树自带模块路径接线）。
- **识别方法**: `find_package` 成功但 `include(<Module>)` 失败 +
  编译命令中该依赖的 include 目录已存在 + 变量被空值覆盖三件套，
  即可与"依赖未安装"和"包内缺文件"两类误诊区分开。
- **同族差异**: 若 `find "<catch2包目录>" -name 'Catch.cmake'` **无输出**，
  那才是打包不完整（另一族问题），修法是把模块纳入打包而非改路径。
