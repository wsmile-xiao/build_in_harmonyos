# qtscxml 6.11.1 适配笔记（Qt SCXML + Qt State Machine，OHOS PC）

## 编译环境
- 构建系统: cmake（Qt6 QtScxml/QtStateMachine 模块仓库）
- 编译日期: 2026-08-30（引入 qtdeclarative 完整 QML 构建）
- 编译器: clang 15 (OHOS aarch64)
- 状态: built

## 版本与来源
- 官方归档: `qtscxml-everywhere-src-6.11.1.tar.xz`
- 官方 URL: `https://download.qt.io/official_releases/qt/6.11/6.11.1/submodules/qtscxml-everywhere-src-6.11.1.tar.xz`
- SHA256: `8e495245e5d1fe75de612c8a07e4043635407a1979bb1dd588f1751d1390203f`
  （设备实测 sha256sum 与 download.qt.io 官方 .sha256 一致；tuna 镜像同哈希复验一致）
- 顶层目录: `qtscxml-everywhere-src-6.11.1/`（conan source() 已 strip_root）

## 模块构成与依赖
| 模块 | CMake 目标 | 依赖（实测 DT_NEEDED）| 本配方构建 |
|------|-----------|------|-----------|
| QtScxml | Qt6::Scxml | Qt::Core | ✅ |
| QtStateMachine | Qt6::StateMachine | Qt::Core + Qt::Gui（qeventtransition）| ✅ |
| QtScxmlQml | Qt6::ScxmlQml | Qt6Scxml + Qt6Qml（+Qt6Network）| ✅（scxml-qml feature）|
| QtStateMachineQml | Qt6::StateMachineQml | Qt6StateMachine + Qt6Qml（+Qt6Gui/Network）| ✅（statemachine-qml feature）|
| QScxmlEcmaScriptDataModelPlugin（scxmldatamodel 插件）| 插件目标 | Qt6Scxml + Qt6Qml | ✅（scxml-ecmascriptdatamodel feature）|
| QML 模块 QtScxml / QtQml.StateMachine（qmldir + 插件 so）| qt_internal_add_qml_module | Qt::Qml | ✅ 安装到 qml/ 目录 |
| qscxmlc 编译器工具 | libexec 内工具 | Qt::CorePrivate | ✅（install 到 libexec，不产生 bin/）|

关键 feature（configure.cmake，引入 qtdeclarative 后全部自动开启）：
- `scxml`/`statemachine` 恒开。
- `scxml-qml`/`statemachine-qml`/`scxml-ecmascriptdatamodel` 条件 `TARGET Qt::Qml` —— 由
  qtdeclarative/6.11.1 提供，全部 yes（config.summary 实测）。
- `qeventtransition` 需要 `TARGET Qt::Gui` —— qtbase/6.11.1 提供 Gui，启用。

关键依赖机制：
- `find_package(Qt6 ... QUIET CONFIG OPTIONAL_COMPONENTS Gui Qml QuickTest)` 的 OPTIONAL
  组件解析走 **QT_ADDITIONAL_PACKAGES_PREFIX_PATH**（Qt6Config.cmake 内层 find_package，
  NO_DEFAULT_PATH），**不读 CMAKE_PREFIX_PATH** → generate() 必须同时设置两个变量
  （均 = qtbase+qtdeclarative package_folder 拼接，见 #9：必须用 CMake list 分隔符
  分号 ";"，**不能**用 os.pathsep 冒号）。

## 编译步骤

```bash
# 在 worktree 内运行权威 CI（一次构建：L0 质量门禁 + conan create + L1/L4/L5 验证）
CI_PACKAGES='archives/q/qtscxml/6.11.1' ci/conan/build_and_test.sh
# 或单独 conan create：
conan create archives/q/qtscxml/6.11.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --build=qtscxml/*
```

配方要点（逐项对照 qtsvg/6.11.1 模板）：
- `QT_QMAKE_TARGET_MKSPEC=harmonyos-clang`，依赖 `qtbase/6.11.1` + `qtdeclarative/6.11.1`。
- qtbase/qtdeclarative 均为 cmake_find_mode "none"：`CMAKE_PREFIX_PATH` 与
  `QT_ADDITIONAL_PACKAGES_PREFIX_PATH` 均指向两者 package_folder 的**分号分隔**
  CMake list（`;`.join，见 #9 根因）；
  `CMAKE_MODULE_PATH` 指向 qtbase 安装的 `lib/cmake/Qt6/platforms`（Platform/HarmonyOS.cmake）。
- **build() 阶段 LD_LIBRARY_PATH**（conanbuild 环境无宿主依赖 loader 路径）：QML 构建阶段
  会执行 qtdeclarative 包内 host 工具（qmltyperegistrar/qmlcachegen/qmlimportscanner，
  安装于包内 libexec/，OHOS aarch64 ELF）。不加 LD_LIBRARY_PATH 会在 QML 类型注册步
  骤失败：`Error loading shared library libQt6Core.so.6`（qmltyperegistrar）。
  故 build() 将 qtbase+qtdeclarative 的 lib 目录经 conan.tools.env 注入 configure/build 全程。
- OHOS ELF 签名（`_sign_installed_elfs`，llvm-objcopy + binary-sign-tool sign -selfSign 1），
  QML 插件 so 同样纳入签名。
- 上游测试: `QT_BUILD_TESTS=ON` + `QT_BUILD_TESTS_BY_DEFAULT=OFF`，显式构建全部 17 个
  测试目标后 `ctest -R '^(...17 目标...)$'` 运行。运行环境：QT_QPA_PLATFORM=offscreen、
  LD_LIBRARY_PATH 追加 qtbase/qtdeclarative/构建树 lib+bin、**QML2_IMPORT_PATH 追加构建树
  qml 暂存目录（QtScxml 与 QtQml/StateMachine 的 qmldir+插件）与 qtdeclarative 包 qml/ 目录**
  （Qt 测试基建不会自动注入本构建新产 QML 模块的导入路径）。
  上游 tests/auto 全量注册 17 个可执行测试：scxmlcoutput 4 + qstatemachine 2 +
  compiled/dynamicmetaobject/scxml_parser/scion/statemachine/statemachineinfo 6 +
  qml 3（qqmlstatemachine/qqmlstatemachinemetatype/scxmlqmlcpp）+ qmltest 2
  （scxmlqml/statemachineqml，QUICK_TEST_MAIN 可执行体，工作目录=源码目录）。
  ctest -N 共 19 目标 = 17 上游 + 2 个 CMake 配置测试（module_includes/test_qtscxml_module，
  无独立可执行，不在运行口径内）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | find_package(Qt6) 找不到 Qt6Scxml/Qt6StateMachine | qtbase 用 cmake_find_mode "none"，CMAKE_PREFIX_PATH 不覆盖模块配置 | generate() 设 CMAKE_PREFIX_PATH=qtbase+qtdeclarative；test_package 显式设 Qt6_DIR / Qt6Scxml_DIR / Qt6StateMachine_DIR |
| 2 | OPTIONAL_COMPONENTS（Qml/QuickTest）静默找不到 | Qt6Config.cmake 内层 find_package 走 NO_DEFAULT_PATH，只查 QT_ADDITIONAL_PACKAGES_PREFIX_PATH | generate() 额外设 QT_ADDITIONAL_PACKAGES_PREFIX_PATH（与 CMAKE_PREFIX_PATH 相同拼接值） |
| 3 | SONAME/SOVERSION 丢失风险 | CMake 不识别 HarmonyOS 平台 | CMAKE_MODULE_PATH 指向 qtbase 的 platforms 目录 |
| 4 | QML 类型注册失败：qmltyperegistrar 报 `Error loading shared library libQt6Core.so.6` + 大量 symbol not found | qtdeclarative 包内 libexec 的 host 工具（arm64 ELF）在 conanbuild 环境运行，无宿主依赖 LD_LIBRARY_PATH | build() 用 conan.tools.env 把 qtbase+qtdeclarative lib 目录加入 LD_LIBRARY_PATH，包裹 configure()+build() 全程 |
| 5 | QML/qmltest 测试找不到 QtScxml / QtQml.StateMachine 模块 | Qt 测试基建不会自动注入本构建新产 QML 模块导入路径 | QML2_IMPORT_PATH = 构建树 qml/（qmldir 暂存）+ qtdeclarative 包 qml/ |
| 6 | 测试运行找不到共享库 | cmake_find_mode "none" 依赖不在默认 loader 路径（测试可执行体 RUNPATH 已含依赖 lib 目录，LD_LIBRARY_PATH 为双保险） | LD_LIBRARY_PATH 加 qtbase lib + qtdeclarative lib + 构建树 lib/bin |
| 7 | 安装产物在 OHOS 无法加载/执行 | 缺 .codesign 段 | package() 内 _sign_installed_elfs() 重新签名（含 QML 插件 so） |
| 8 | CI 权威流程需外网 | qtdeclarative 依赖 qtshadertools/6.11.1，不在本地 conan 缓存，conan create --build=missing 需远端解析；L0i registry 探测需远端 | 网络恢复后跑 FULL CI；qtshadertools 远端已有匹配预编译二进制（package id 57ffd8...），首次 conan create 直接 download，无需本地构建 |
| 9 | 引入 qtdeclarative 后 FULL CI configure 直接失败：`find_package(Qt6 ... COMPONENTS BuildInternals)` 报 Could not find Qt6Config.cmake | generate() 用 `os.pathsep.join()`（Linux 下 = 冒号）拼接两前缀写入 `CMAKE_PREFIX_PATH`/`QT_ADDITIONAL_PACKAGES_PREFIX_PATH`；CMake list 型缓存变量分隔符是**分号**，`A:B` 单字符串被当成一个不存在的路径，find_package 静默搜不到。此前单依赖配置时只有一个前缀、无分隔符，侥幸通过 | 改为 `";".join(...)`（CMake list 分隔符）。对照实验确认：单前缀 FOUND；`qtb:qtd` NOTFOUND；`qtb;qtd` FOUND（Qt6Config.cmake 正常执行）。`QT_ADDITIONAL_PACKAGES_PREFIX_PATH` 同步用分号（Qt6Config.cmake 直接按 CMake list 消费 cache 变量，不做冒号拆分） |
| 10 | FULL CI L5c 门禁 fail：3 个 QML 插件导出 .cmake 含 `IMPORTED_NO_SONAME "TRUE"` | Qt QML 插件（libqtqmlstatemachineplugin.so 等）按上游 Qt 标准导出即 IMPORTED_NO_SONAME（QML 插件由 QML 引擎 dlopen 加载，无 SONAME 需求，.so 本体亦无 DT_SONAME 属正常）；同仓库已发布的 qtdeclarative/6.11.1 有 57 个、qtbase/6.11.1 有 7 个相同文件仍交付 CI，属 L5c 已知误报 | 不改配方（改导出行为会偏离上游）；L5a/L5b（核心库 DT_SONAME=libQt6*.so.6 相对路径、DT_NEEDED 无绝对路径）全部通过；L5c 误报已记录，Build Summary 1/1 不受 L5 标签影响 |

无源码补丁（purity 适配，仅配方层修改；patches/ 目录保留并附说明）。

## 依赖版本
- qtbase 6.11.1（含 Core/Gui/Widgets/Network/Xml）
- qtdeclarative 6.11.1（Qml/Quick/QuickTest 等；依赖 qtbase + qtshadertools 6.11.1）
- 构建期源码由 conan get() 从五镜像列表直连下载（sha256 与官方一致）

## 验证结果
- **权威 FULL CI（2026-08-30，网络恢复后，profile ohos-aarch64，conan create 全量重建）**：
  - 依赖图：qtshadertools/6.11.1 首次从 ohpcd 远端 **download 预编译二进制**
    （package id 57ffd8c720a5bfee7e8827990cd6550a49181c1b），未触发本地构建。
  - configure 成功（五 feature 全 yes），17 个测试目标全部构建，
    **`100% tests passed, 0 tests failed out of 17`**
    （17 个上游测试在 build() 内经 `ctest --output-on-failure -R "^(…17 目标…)$"` 真实运行；
    ctest 退出码 0 —— conanfile 以 self.run 执行，非零会中断 conan create）：
    | 目标 | 结果 | 耗时 |
    |------|------|------|
    | tst_scxmlcoutput_default | Passed | 0.09s |
    | tst_scxmlcoutput_namespace | Passed | 0.08s |
    | tst_scxmlcoutput_path | Passed | 0.07s |
    | tst_scxmlcoutput_arguments | Passed | 0.08s |
    | tst_compiled | Passed | 2.14s |
    | tst_dynamicmetaobject | Passed | 0.13s |
    | tst_scxml_parser | Passed | 0.08s |
    | tst_scion | Passed | 143.67s |
    | tst_statemachine | Passed | 13.05s |
    | tst_statemachineinfo | Passed | 0.12s |
    | tst_qqmlstatemachine | Passed | 0.17s |
    | tst_qqmlstatemachinemetatype | Passed | 0.15s |
    | tst_scxmlqmlcpp | Passed | 1.21s |
    | tst_statemachineqml | Passed | 1.29s |
    | tst_scxmlqml | Passed | 0.16s |
    | tst_qstate | Passed | 0.09s |
    | tst_qstatemachine | Passed | 13.47s |
  - test_package 消费者（test_qtscxml：QScxmlStateMachine 解析+启动内联 SCXML；
    QStateMachine 双状态启动）构建并运行 PASS（`smoke test OK`）。
  - 门禁：L0 pass / L1 pass（17 上游 ctest + test_package 真实执行，L1e 破坏性反向验证
    确认真依赖）/ L2 skip（无 bin/）/ L4 pass（patches 干净，本包无补丁）/
    **L5c fail = 已知误报**（3 个 QML 插件导出 .cmake 的 `IMPORTED_NO_SONAME "TRUE"`
    是上游 Qt QML 插件标准导出，见 #10；L5a/L5b 全过）；Build Summary 1/1 100%，
    脚本仅在 FAILED>0 时 exit 1、L5 标签不计入 FAILED，日志末尾已打印
    "All packages built and tested successfully ✅" → 最终退出码 0，判定 PASS。
  - 版本证据：CI 所用 conanfile.py（conan 缓存导出
    /storage/…/.conan2/p/qtscx9704e2c63affe/e，2026-08-30 21:10 修改、21:13 export）与
    最终提交版逐字一致（sha256 均 bb49654a9652404b17be733edfdd0ff0a9cdcb8e34561b258886f63329925ef3）。
  - 安装产物：4 库（SONAME=libQt6*.so.6）+ 2 QML 模块（qml/QtScxml、
    qml/QtQml/StateMachine，各含 qmldir + 插件 so + plugins.qmltypes）+
    scxmldatamodel 插件 + qscxmlc + metatypes + cmake 配置；全部 ELF（含 5 个插件 so）
    经 _sign_installed_elfs() 重签名（.codesign 段在位）。
- ELF 签名：llvm-objcopy 去旧 .codesign + binary-sign-tool sign -selfSign 1，
  覆盖 lib/、qml/、plugins/、libexec/ 全部 ELF（L5a/L5b 门禁通过）。

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方（qtbase/6.11.1 + qtdeclarative/6.11.1 依赖、ELF 签名、17 个上游测试全量构建运行、QML 插件构建并签名） |
| conandata.yml | 官方 Qt 镜像源（清华/中科大/腾讯云/阿里/download.qt.io）+ SHA256 |
| manifest.yaml | 版本级 manifest（ARCHIVE-SPEC v2.0，upstream 17/17） |
| notes.md | 本文件 |
| test_package/ | 消费者测试（链接 Qt6::Scxml + Qt6::StateMachine）+ MANIFEST.yml |
| patches/README.md | 说明无需源码补丁 |

## 注意事项
- 依赖顺序: qtbase/6.11.1 → qtdeclarative/6.11.1（qtshadertools/6.11.1 为其依赖）→ qtscxml/6.11.1。
- 权威 CI 需要设备外网（qtshadertools 图解析 + L0i registry 探测）；FULL CI 已于
  2026-08-30 执行通过（见"验证结果"），后续重跑直接
  `CI_PACKAGES='archives/q/qtscxml/6.11.1' ci/conan/build_and_test.sh`。
- test_package 的 find_package 依赖 Qt6_DIR（qtbase）与 Qt6Scxml_DIR/Qt6StateMachine_DIR
  （本包）缓存变量（cmake_find_mode "none" 依赖不产生 CMakeDeps 配置）；消费者如需 QML
  类型，将 QML2_IMPORT_PATH 指向本包 qml/ 与 qtdeclarative 包 qml/ 即可。
- 离线验证的 test_package 运行曾遇到设备文件系统（hmdfs 挂载，属主 20001006:file_manager、
  执行 uid 20020085 仅持 CAP_DAC_OVERRIDE）对自建安装目录的 loader 访问限制，属验证环境
  权限特性；同字节库从 conan 包目录/构建树加载与运行均正常（17/17 上游 ctest 于
  2026-08-30 权威 FULL CI 全量 PASS，消费者 smoke test 亦 PASS），与配方无关。
