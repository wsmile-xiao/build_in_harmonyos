# libkode 0.0-git20251106.580356d 适配笔记

## 编译环境
- 构建系统: cmake (C++17)
- 编译日期: 2026-09-26
- 编译器: clang/clang++（HarmonyOS PC aarch64 工具链）
- 状态: built（真机 rule4 门禁验证中，尚未发布）

## 上游溯源与版本
- 上游仓库: https://github.com/cornelius/libkode（Cornelius Schumacher，原 kode 项目/KDSOAP 拆分）
- 上游无 tag 发布，版本为 git snapshot：commit `580356d`（2025-11-06）。
- 官方源码归档: `https://github.com/cornelius/libkode/archive/580356d2a2f0d890e5482808f578874ad3900442.tar.gz`
- sha256: `30a52fb888592686cb8c2eeb970cbe9d86dcd02f90c4e553ee50e2a770c00a33`

## 编译步骤
1. `conan create . --profile=ohos-aarch64`（conanfile.py 为唯一构建输入）
2. `source()` 下载并解压源码（strip_root）。
3. `-Dlibkode_QT6=ON`（走 Qt6 路径）、`-DBUILD_SHARED_LIBS=OFF`；依赖 `qtbase/6.11.1`
   （提供 Qt6::Core/Network/Xml/Test）。
4. `0001-add-install-rules.patch` 补齐三个静态库与头文件的 install() 规则。
5. `cmake.configure() && cmake.build()`。
6. `ctest -N` 盘点 + `ctest --output-on-failure --no-tests=error` 运行上游 3 个 QtTest 用例
   （offscreen QPA + 依赖 LD_LIBRARY_PATH），输出 HMBS 证据标记。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `find_package(Qt6 ... COMPONENTS Core Network Xml Test)` 需要 Qt6::Test | qtbase 使用 cmake_find_mode=none，CMakeDeps 不生成路径 | 选 `qtbase/6.11.1`（FEATURE_testlib=ON），手工写 `conan_cmakedeps_paths.cmake` 预置 CMAKE_PREFIX_PATH（adwaita-qt/alkimia/accessibility 既有先例） |
| 2 | 上游无 install() 规则，`cmake.install()` 装不出 lib/ + include/ | libkode 每个子目录 CMakeLists 只有 add_library，无 install | 补丁 `0001-add-install-rules.patch`：为 kode/xmlcommon/xmlschema 加 install(TARGETS ... ARCHIVE) + install(FILES <头文件列表> DESTINATION include)（扁平 include 与上游扁包含路径一致） |
| 3 | 库名不随 Qt6 加 `-qt6` 后缀 | 顶层 CMakeLists 设置的是 `libkode_LIBRARY_QTID`，但子目录 `set_target_properties` 引用的是 `${kode_LIBRARY_QTID}`（变量名不匹配，故 QTID 恒为空） | package_info 声明 `cpp_info.libs = ["kode","xmlschema","xmlcommon"]`（产物实为 `libkode.a`/`libxmlcommon.a`/`libxmlschema.a`） |
| 4 | 上游默认 Qt5 | 顶层 CMakeLists `libkode_QT6` 默认 OFF | `generate()` 设 `libkode_QT6=ON` |
| 5 | 真机 preflight compile 报 `Error: 'str' object has no attribute 'fileno'`，`conan create` 在 `_run_upstream_tests` 的 `self.run(..., stdout=log_path)` 处崩溃 | Conan 2.x `ConanFile.run()` 的 `stdout` 参数要求可 `fileno()` 的文件型对象，而配方传的是**字符串路径**，导致 subprocess 层对 str 取 fileno 报错 | `_run_upstream_tests` 与 `_ctest_discover` 改为先 `open(log_path, "w")` 拿到流对象，再把流对象传给 `stdout=`；写日志文件后再从同一路径解析 ctest 输出（计数字面量仍来自真实 ctest 输出，未改变口径） |
| 6 | 真机 preflight test_package 阶段 `conan create` 报 `CMakeLists.txt:8 (find_package)` `By not providing "Findqtbase.cmake"...`，configure 失败 | test_package 用 CMakeDeps 的 `find_package(libkode)`，生成的 `libkodeConfig.cmake` 会调用 `find_dependency(qtbase)`；而 qtbase 用 `cmake_find_mode=none` 且只装真实 `Qt6Config.cmake`（无 `qtbaseConfig`），故 find_dependency(qtbase) 找不到配置（audiocd 已踩过的同款场景） | test_package 改为 audiocd 先例：不消费 CMakeDeps 生成的 libkode target，改用 `find_package(Qt6)`（通过手工 `conan_cmakedeps_paths.cmake` 预置 qtbase lib/cmake）+ `find_path`/`find_library` 直链三个静态库（kode/xmlschema/xmlcommon）；`generators` 精简为 `CMakeToolchain`。8 个断言与 HMBS 标记不变 |
| 7 | 真机 preflight test_package 阶段 CMake Generate 报 `LIBKODE_INCLUDE_DIR ... set to NOTFOUND`，`find_path(LIBKODE_INCLUDE_DIR class.h)` 找不到头文件 | `0001-add-install-rules.patch` 三个 hunk 的**行数计数错误**（`+46,9` 应为 `+46,12`、`+27,6` 应为 `+27,7`、`+43,6` 应为 `+43,7`）。GNU patch / git apply 把计数当提示，lenient 地把每个 hunk 尾部多出的 add 行静默丢弃：code_generation 的 3 条 `install()` 全丢（`class.h` 从未装入 flat `include/`），common/schema 的各丢 1 条 subdir 镜像 install。主库 build/install 仍退出 0（仅安装残缺），上游 3 个用例也照常通过，因此只有 test_package 的 find_path 暴露出来 | 修正 `patches/0001-add-install-rules.patch` 三个 hunk 计数为正确值：`+46,12`、`+27,7`、`+43,7`。用 `git apply`（与 GNU patch 同款 lenient 计数）对重建的 pristine 源码整树应用，确认三个 CMakeLists 均得到完整 `install(TARGETS ... ARCHIVE DESTINATION lib)` + 两条 `install(FILES ... DESTINATION include[/subdir])`（3/3/3）。`.patchtest/` 同步更新为修正后的一致输出 |

## 源码修改
- `patches/0001-add-install-rules.patch`：仅为 3 个子目录 CMakeLists 追加 install() 规则，
  未改动任何源文件/行为。

## 依赖版本
- qtbase/6.11.1（Qt6 Core/Network/Xml/Test for HarmonyOS PC）

## 上游测试审计（R51）
- **统计单位**：ctest 注册条目（`upstream_test_count_method: ctest_entries`）。
- **总数**：3 个 ctest 条目，来源 `autotests/CMakeLists.txt`：
  1. `tst_xmlelement`（XSD::XmlElement 构造/赋值）
  2. `tst_element`（XSD::Element 构造/赋值）
  3. `tst_group`（XSD::Group 构造/赋值）
- 三个用例均为纯逻辑 QtTest（拷贝/移动构造 + 赋值），不依赖网络/文件/窗口，可离线执行。
- 实测结果以真机 `conan create` 内 ctest 输出为准（HMBS 证据标记），待 rule4 真机轮回填。

## 验证结果（真机 evidence 轮回填）
```bash
# ctest -N → discovered 3
# ctest --output-on-failure → executed/passed/failed（真机实测）
```

## 交付物
- `archives/l/libkode/0.0-git20251106.580356d/`：
  `conanfile.py`、`conandata.yml`、`manifest.yaml`、`notes.md`、
  `patches/0001-add-install-rules.patch`、`test_package/`
- 软件级：`archives/l/libkode/manifest.yaml`、`archives/l/libkode/README.md`

## 注意事项
- libkode 是库（library）类型，产物仅静态库 + 头文件，无 bin/ 可执行文件，故**不需要**
  `commands.json`。
- 静态库依赖 Qt6 运行时：下游链接需同时链 Qt6::Core/Network/Xml（test_package 已处理）。
- 配方与补丁为工作树修改，尚未 commit/push；待真机 rule4 门禁通过后由 HMBS 统一提交推送。
