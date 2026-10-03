# 预分析报告: qtdeclarative 6.11.1.1（原适配）→ 6.11.1.2（provider 修订）

> 生成日期: 2026-08-25
> 官方源码: https://mirrors.tuna.tsinghua.edu.cn/qt/official_releases/qt/6.11/6.11.1/submodules/qtdeclarative-everywhere-src-6.11.1.tar.xz
> SHA256: `52e670f670b0304f534b24f98c47ceb8a41bb710464414ebc9527ec71cc86aa4`

## 1. 版本与 R37

- `qtdeclarative/6.11.1` 已在 OHPCD 远端发布，且本轮 recipe 与已发布 recipe 不同。
- 按 R37 不能覆盖同名版本，当前适配版本使用 `qtdeclarative/6.11.1.1`。
- 配方版本号为 `6.11.1.1`，但源码和 Qt ABI/SONAME 仍对应上游 `6.11.1`，recipe 内使用 `_qt_version = "6.11.1"` 区分包版本与上游版本。

## 2. 构建系统

- 上游使用 CMake 和 Qt `BuildInternals` 构建。
- 直接依赖:
  - `qtbase/6.11.1`
  - `qtshadertools/6.11.1`
- W0 真机远端检查已确认两个依赖 recipe 均在 `ohpcd`:
  - `qtbase/6.11.1#714d84d05331908398556fe7145473c7`
  - `qtshadertools/6.11.1#7bc99312dbc9fbd7b019df8cbd5bf873`
- 当前构建打开上游测试生成并启用默认全量测试构建:
  - `QT_BUILD_TESTS=ON`
  - `QT_BUILD_TESTS_BY_DEFAULT=ON`
  - `QT_BUILD_EXAMPLES=OFF`
  - `QT_BUILD_EXAMPLES_BY_DEFAULT=OFF`
- 上游 `tests/auto/` 测试套件并非为空：Qt Declarative 6.11.1 约包含 10372 个测试文件、550 个 `CMakeLists.txt` 和 22 个顶层测试目录（如 `qml/`、`quick/`、`qmlnetwork/`、`qmltest/`）。本轮由 Qt CMake 图启用全部上游测试目标，并在 CI 中运行完整 CTest 注册表，不再使用固定目标清单或 `-R` 过滤。

## 3. Qt 模块关系

- `qtdeclarative` 主要提供 QML engine、QML models、QML worker script、Qt Quick 和一组 Quick Controls/Dialogs/QML tooling 产物。
- CMake 消费者应优先使用 Qt 原生安装的 `Qt6*Config.cmake`，因此 `package_info()` 保持 `cmake_find_mode=none`，避免 Conan 生成的不完整 CMake config 覆盖 Qt 自带 config。
- 下游 Conan recipe 可能声明 `qtdeclarative::quick`，本轮补充以下组件元数据:
  - `qtdeclarative::qml`
  - `qtdeclarative::qmlmodels`
  - `qtdeclarative::qmlworkerscript`
  - `qtdeclarative::quick`

## 4. HarmonyOS 关键适配点

- CMake 在 OHOS host 上缺少 `Platform/HarmonyOS.cmake`，复用 Qt 相关模块做法，将 CMake 平台规则呈现为 Linux，同时保留 OHOS clang driver 的目标三元组。
- `qtshadertools` 提供的 `qsb` 会在构建 Qt Quick shader 时作为 host tool 运行。其 RUNPATH 只覆盖自身包内 lib，构建期需要把 `qtbase/lib` 和 `qtshadertools/lib` 注入 `LD_LIBRARY_PATH`。
- 真机 job 存储拒绝创建 symlink。CMake 生成的 `cmake_symlink_library` 规则会在编译阶段失败，例如 `QuickDialogs2Utils` 链接后创建 `libQt6QuickDialogs2Utils.so.6` / `.so` 报 `Permission denied`。
- 可行 workaround: `cmake.configure()` 后扫描 build tree 中的 `.make` 文件，将 `$(CMAKE_COMMAND) -E cmake_symlink_library` 替换成 recipe 生成的 Python copy helper，使用常规文件副本代替 `.so.6` / `.so` symlink。
- package 阶段也不能依赖 `os.symlink()`，需要为所有 `libQt6*.so.6.11.1` 物化对应 `.so.6` 和 `.so` 常规文件副本。
- HMDFS 的 Make jobserver 依赖 `mkfifo`，而启用上游测试时 Qt AUTOMOC 还可能出现生成文件竞态；主库和全部上游测试目标统一通过 CMake `-j1` 串行构建，同时将 `CMAKE_AUTOGEN_PARALLEL=1` 固定为单线程，CTest 运行完整注册表。
- OHOS 可运行 ELF 需要签名，package 阶段跳过 symlink，仅对真实 ELF 文件重签名。

## 5. 测试计划

- 上游官方测试规模: `tests/auto/` 约 10372 个测试文件、550 个 `CMakeLists.txt`、22 个顶层测试目录。
- 上游官方测试执行计划: 构建阶段启用 `QT_BUILD_TESTS=ON`、
  `QT_BUILD_TESTS_BY_DEFAULT=ON`，执行 `ctest -N --no-tests=error` 保存
  完整注册表，再执行 `ctest --output-on-failure --no-tests=error`，不使用
  `-R` 目标过滤。CI 日志是注册、通过、失败和跳过统计的唯一依据。
- 不再通过减少测试目标规避依赖问题。Quick/QML tooling/debugger/windowed/
  qmltest 等目标若受 Qt 上游 feature、依赖、QPA、host tool 或设备能力门控，
  必须在本次 CTest 日志中保留对应构建或运行结果。
- 逐项技术清单: `test_package/UPSTREAM_TEST_INVENTORY.md` 按上游
  `v6.11.1` 的精确 `tests/auto` 文件路径记录全部 10372 项的第一适用
  构建或运行门控；`test_package/UPSTREAM_TEST_MATRIX.md` 提供 22 个顶层区域
  和 QML 引擎、工具、debugger、可选特性子族的分组解释。内容覆盖 Qt 模块/
  私有目标、host tools/进程 IPC、安装态 QML import tree、QPA/窗口/输入/
  GPU/RHI/OpenGL、网络/SSL/SQL，以及 Android/wasm 专属 harness；
  `tst_qqmlextensionplugin` 缺少 build-tree 安装态 QML testdata 的 QTest fatal
  也作为实测证据记录。
- 统计边界: 当前 N=10372，recipe 将全部由上游 CMake 启用的测试目标纳入
  默认构建并执行完整 CTest；不把 CMake 未注册、CTest 跳过或 consumer
  smoke test 冒充上游通过，最终通过率按 CI 日志实际结果计算。
- `test_package` 必须真实链接并使用 `Qt6::Qml` 与 `Qt6::Quick`。
- 运行时设置:
  - `QML_IMPORT_PATH`
  - `QML2_IMPORT_PATH`
  - `QT_QPA_PLATFORM=offscreen`
  - 可用时设置 `QT_QPA_PLATFORM_PLUGIN_PATH`
- 测试程序应创建 `QGuiApplication`、`QQmlEngine`，加载 inline `import QtQuick` 的 `Item`，并断言:
  - QML object 创建成功
  - object 可转为 `QQuickItem`
  - 自定义属性值正确
  - Quick item 尺寸属性正确
  - `QJSEngine` 表达式求值正确
- 测试二进制在 OHOS 上执行前需要用 `binary-sign-tool` 自签名。

## 6. 已验证结果

- r1 shadow CI 使用 `6.11.1`，L0j 因版本碰撞失败。
- r2 shadow CI 使用 `6.11.1.1`，构建期因 `cmake_symlink_library` 创建 symlink 被拒绝失败。
- r3 shadow CI 使用 `6.11.1.1`，加入 symlink-copy workaround 后通过。
- r3 运行目录: `/storage/Users/currentUser/ohos-test-runs/currentUser-qtdeclarative-qtdeclarative-6.11.1.1-codex-20260825-r3-shadow-ci-r3-20260825-194603-1705`
- `conan create` 通过，包引用:
  `qtdeclarative/6.11.1.1#5ac69601067437611341923ad78b4179:01613e54aaa58fa7f2115b0cb13c50b04cfa9c72#6d276e028c68d1116934a12cb10ac227`
- test_package 输出:
  `QtDeclarative OK: QtQuick item instantiated, answer=42, eval=14`
- 历史 L0/L1/L4/L5 通过；其中历史 L1 仅表示消费者侧 `test_package` 执行和 R34 负向验证通过。全量上游 CTest 已接入 recipe，新的 CI/真机运行必须重新核对最终统计；无可运行 OHOS 目标时现在会直接失败而不是跳过。历史 L2 为非阻塞 skip，原因是多个 `qml* --version/--help` 失败。
- 产物确认: `find <package_folder> -type l` 返回 `0`，`libQt6Qml.so*` 与 `libQt6Quick.so*` 均为常规文件副本。

## 7. 后续关注

- test_package configure 仍提示 CMake 未识别 `Platform/HarmonyOS`，目前不影响配置、编译和执行。
- `conan-build-test` 曾在并行 `-j20` 下出现 Qt AUTOMOC 生成文件竞态（`moc_qqmlbuiltins_p.cpp` 尚未生成即被聚合编译），同时 HMDFS 报告 `make: jobserver mkfifo ... Operation not permitted`；recipe 现已对主库和全部上游测试目标固定 `-j1`，并将 CMake AUTOMOC worker pool 固定为单线程，CTest 仍保持真实执行。
- 如后续要进一步扩大上游 Qt Declarative 官方测试，需要单独评估测试耗时、显示后端、QML plugin 路径、派生 host tools 和签名需求。

---

## 追加说明（2026-10-02，6.11.1.2 provider 修订）

`qtdeclarative/6.11.1.1` 已由平台合入并发布，但其配方仍声明旧的 `qtbase/6.11.1`（下游必须自行 `override=True` 收敛）。按 R37 新增本修订 `6.11.1.2`，只改 provider 引用（`qtbase/6.11.1.3, override=True`）与版本号；上游源码、补丁、构建与测试逻辑不变。`qtshadertools/6.11.1` 与 `qtsvg/6.11.1` 因各自 `.1` 修订未发布而保持不变（L0i R36）。
