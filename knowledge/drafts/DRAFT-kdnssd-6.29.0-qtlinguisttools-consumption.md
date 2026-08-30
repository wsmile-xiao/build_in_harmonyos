# DRAFT-kdnssd-6.29.0-qtlinguisttools-consumption: Qt6LinguistTools 发布版本消费（tool_requires + Qt6LinguistTools_DIR 显式定位）

## 场景

kdnssd 6.29.0（KDE Frameworks 6 Tier1 库）适配到 HarmonyOS PC。上游 CMake/ECM
体系在 configure 阶段通过 `ECMPoQmTools.cmake`（`ecm_install_po_files_as_qm`，
源码调用栈 ECMPoQmTools.cmake:249 → :155 `find_package(Qt6 COMPONENTS LinguistTools)`）
执行 poqm 翻译，需要 Qt6 LinguistTools（lrelease/lupdate/lconvert/lcheck/ltext2id
工具 + `Qt6::LinguistTools` CMake 宏模块）。

Qt 6 中 LinguistTools 不是独立源码模块，其实体由 qttools 构建产生；qtbase 包
**不包含** Qt6::LinguistTools 组件。ohpcd 制品仓将之独立发布为
`qt6linguisttools/6.11.1`（与当前 Qt 6.11.1 基线匹配），并提供
`Qt6LinguistToolsConfig.cmake` 与上述 bin 工具。

## 问题（error_signature → root_cause）

`conan create` 时 configure 失败，典型日志：

```
Could NOT find Qt6LinguistTools (missing: Qt6LinguistTools_DIR)
CMake Error at .../ECMPoQmTools.cmake:155 (find_package):
  Found package configuration file:
    .../qtbase.../lib/cmake/Qt6/Qt6Config.cmake
  but it set Qt6_FOUND to FALSE so package "Qt6" is considered to be NOT FOUND.
  Reason given by package: Failed to find required Qt component "LinguistTools".
  Expected Config file at ".../qtbase.../lib/cmake/Qt6LinguistTools/Qt6LinguistToolsConfig.cmake" does NOT exist
```

根因：**Qt6Config.cmake 的组件解析锚定 `Qt6_DIR`（qtbase 包内 lib/cmake/Qt6）的
相对路径**。`find_package(Qt6 COMPONENTS LinguistTools)` 会先在 Qt6_DIR 旁找
`Qt6LinguistToolsConfig.cmake`；即使 `qt6linguisttools` 独立包已安装、其 builddirs
已通过 CMAKE_PREFIX_PATH 暴露，组件查找仍沿 Qt6_DIR 相对路径走，找不到独立包内的
`Qt6LinguistToolsConfig.cmake`，于是判定 Qt6 组件 LinguistTools 缺失。这是
"Qt 组件分包发布 + Qt6_DIR 锚定"的组合问题，单纯加 CMAKE_PREFIX_PATH 不解决。

## 修复（solution）

在 Conan 配方中分三步接入：

1. **构建期依赖声明**（LinguistTools 是构建期工具链，不是运行期库）：

   ```python
   def build_requirements(self):
       self.tool_requires("ecm/6.26.0")
       self.tool_requires("qt6linguisttools/6.11.1")   # 与 Qt 6.11.1 匹配，ohpcd 已发布
   ```

2. **显式钉住组件目录**（关键）：在 `generate()` 的 CMakeToolchain 变量中直接设置
   `Qt6LinguistTools_DIR`，让 ECMPoQmTools 的 `find_package` 命中独立包：

   ```python
   ltt = self.dependencies.build.get("qt6linguisttools")
   if ltt:
       tc.variables["Qt6LinguistTools_DIR"] = os.path.join(
           ltt.package_folder, "lib", "cmake", "Qt6LinguistTools")
   ```

3. **paths 文件追加**（保险）：在 conan_cmakedeps_paths.cmake 中把
   `qt6linguisttools` 的 `lib/cmake`、`lib/cmake/Qt6LinguistTools` 追加入
   `CMAKE_PREFIX_PATH`/`CMAKE_MODULE_PATH`，使 `find_package(Qt6 COMPONENTS
   LinguistTools)` 与宏加载均可解析。

禁止 `--build=missing` 从源码重编 qttools/qttools 依赖链（R36：依赖必须先发布）。
Naming 注意：Conan 包名必须全小写（`qt6linguisttools`），归档目录可保留
`Qt6LinguistTools` 大小写。

## 验证

`conan create kdnssd/6.29.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=same`：

- CMake configure 通过：ECMPoQmTools `find_package(Qt6 COMPONENTS LinguistTools)` 成功
  （不再报 Qt6LinguistTools_DIR 缺失）
- `libKF6DNSSD.so` 构建成功，`zeroconf-browser` 示例链接成功
- 上游 ctest 零入口证据（kdnssd 无 autotests，`No tests were found`）rc=0
- test_package ctest **2/2 Passed**：`test_kdnssd`（isAvailable()=2 Unsupported，
  getLocalHostName()=''，finished emitted=1）+ 鸿蒙特有 `test_kdnssd_ohos`
  （断言 dummy backend：isAvailable()==Unsupported、空 hostname、startBrowse()
  同步 finished、services() 为空）
- `conan-verify` G1/G0/G2/G3/G4/L2/L4/L5 全 PASS
- finish W3 本地 CI：L0/KC 全过（r04 经 goaccess 基线噪音豁免后 JC3 pass，
  Pass rate 100%）

## 可复用边界（适用 / 不适用）

适用：
- 含 poqm 翻译（ECMPoQmTools `ecm_install_po_files_as_qm`）的 KF6/Qt6 库
  在 HarmonyOS PC 的适配（kdnssd 为实测案例）
- 任何 "Qt6 组件由独立包提供、且 Qt6_DIR（主包）与组件包分离" 的 CMake 消费场景：
  组件解析锚定 Qt6_DIR 时，显式 `Qt6<Component>_DIR` 是通解
- 版本严格对齐当前 Qt 基线（Qt 6.11.1 → qt6linguisttools/6.11.1，不得用旧版替代）

不适用 / 注意：
- qtbase 或其他 Qt 主包已自包含 LinguistTools 时无需该处理
- `qt6linguisttools` 未发布到制品仓时，应先发布依赖（R36），不得 `--build=missing` 掩盖
- 库本身无 poqm 翻译（不调用 ecm_install_po_files_as_qm）时无需 LinguistTools
- 本条目是构建期消费路径（L0i 依赖可用性门禁），不是发布后自身消费验证

## 查重差异

- `knowledge/drafts/E326-draft-49FD.kv`：主题为 qttools Qt6::Help 组件缺失 →
  test_package 改用实际产出的 Qt6::UiTools；同为 "Qt6 子模块分包" 家族，但错误
  面（Help 组件 vs LinguistTools 组件）与解法（换组件 vs tool_requires+钉 DIR）
  完全不同，不重复。
- 正式条目（knowledge/graph/*.kv）无 LinguistTools/qttools 消费条目（grep 零命中）。

## 来源

kdnssd 6.29.0 r03（build_in_harmonyos，`archives/k/kdnssd/6.29.0`），
conan-create 日志 `/storage/Users/currentUser/tmp/kdnssd-r03-conan-create4.log`
（SHA-256 `8ee60ddc…`），conan-verify 报告 SHA-256 `270282a9…`。