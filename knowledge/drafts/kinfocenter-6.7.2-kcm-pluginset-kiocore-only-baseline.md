# KDE KCM 插件集包在 KIOCORE_ONLY 基线上的适配：目标可用性矩阵裁剪 + KPluginFactory 消费者测试

> Draft: `DRAFT-KINFOCENTER-672-KCM-KIOCORE-ONLY`
> Stem: `kinfocenter-6.7.2-kcm-pluginset-kiocore-only-baseline` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-KINFOCENTER-672-KCM-KIOCORE-ONLY
- **严重度**: 2
- **类别**: ohos-platform|portability|packaging
- **触发工具**: conan|cmake|ctest
- **阶段**: configure|build|package|runtime

## 错误特征

KCM 插件集包（kinfocenter 6.7.2 实证）在 ohpcd KIOCORE_ONLY kio 基线上
configure 阶段连环报错，每一类缺口对应不同报错形态：

```
# (1) KIOGui/KIOWidgets 消费者
CMake Error: Target "KF6::KIOGui" does not exist.      # about-distro
Target "KF6::KIOWidgets" does not exist.               # samba kcm_samba_static

# (2) pkg-config 工具链（libdrm 制品 .pc prefix=/，跨 worker 漂移）
-- Checking for one of the modules 'libdrm'
CMake Error: The following variables are used in this project, but they
are set to NOTFOUND

# (3) kauth 安装宏（FAKE 后端无 policy-gen 工具）
install(CODE) execute_process(kauth-policy-gen ...) → command not found

# (4) 符号链接 payload（无 systemsettings）
file(INSTALL) cannot create link ... No such file or directory

# (5) 消费者加载（新鲜 ELF 的 .codesign stub）
Cannot load library .../kcm_cpu.so: Permission denied  # EACCES 非 EPERM
```

实际观测（2026-10-03，OHOS aarch64，clang 15 / CMake 4.1 / kio 6.26.0）：

| KCM 模块 | 声明依赖 | 处置 | 结果 |
|----------|---------|------|------|
| about-distro | KIOGui + libdrm + UDev + vulkan/opengl helper | 裁 | configure 通过 |
| helpers(dmidecode) | kauth-policy-gen（FAKE 后端缺失） | 裁 | install 通过 |
| usbview | FindUSB1→pkg-config libusb | 裁 | 跨 worker 确定性 |
| samba | KIOWidgets + KPropertiesDialog | 改→Qt6::DBus/KIOCore | autotests 保住 |
| energy | 上游 Linux 守卫 | 守卫天然跳过 | — |
| 其余 17 个 CommandOutputContext 型 | KCMUtilsQuick/CoreAddons/I18n | 保留 | 全部构建加载 |

## 根因分析

ohpcd 的 kio/6.26.0 制品是 **KIOCORE_ONLY 基线**：只发布
`libKF6KIOCore.so`，`KF6KIOConfig.cmake` 的 KIOGui/KIOWidgets/
KIOFileWidgets find_dependency 分支在构建期已被剪掉（读制品
`KF6KIOTargets.cmake` 可实证只有 `add_library(KF6::KIOCore)`）。
反直觉点：**KSambaShare/KSambaShareData 符号在 KIOCore 内**
（llvm-nm 实证），所以 samba KCM 是"改接"而不是"裁"。

四类连锁缺口的完整链条：

1. **目标缺失**：链接 KF6::KIOGui/KIOWidgets 的目标 configure 失败。
2. **pkg-config 漂移**：libdrm 制品的 .pc 写死 `prefix=/`；FindUSB1
   这类 module 探测在 worker 上可能探到 host x86_64 的同名 .pc，
   把异 ABI 库链进 OHOS 插件——不是必现错误而是"偶发毒链"，
   必须为确定性裁掉。
3. **kauth FAKE 后端**：OHOS kauth 包 `KAUTH_BACKEND_NAME="FAKE"`、
   不带 kauth-policy-gen host 工具；`KAUTH_INSTALL_ACTIONS`/
   `KAUTH_INSTALL_HELPER_FILES` 宏在 install 阶段执行该工具。
4. **符号链接 payload**：上游 kinfocenter"二进制"= 指向
   systemsettings 的 symlink（`ADD_CUSTOM_TARGET ... create_symlink`），
   OHOS 无 systemsettings → 悬空链接 `file(INSTALL)` 失败。

共性尾巴（每个 KDE GUI 包都会撞）：
- 私有 helper 库无 SONAME → 已装插件记录 build-tree 相对
  DT_NEEDED（`../../bin/libKF6*.so`），CWD 一变就解析失败
  （E330/E537 同族）。
- 新鲜链接的 OHOS ELF 带无效 `.codesign` stub 段 → dlopen 报
  `Permission denied`（EACCES），LD_LIBRARY_PATH 根本没被咨询
  （E077 已收，本条把手段前移到 package() 期）。

## 解决方案

### 第一步：目标可用性矩阵（先画表再裁）

```bash
# 逐 KCM 扫四类声明
grep -E "find_package|pkg_check_modules|kauth_install|target_link_libraries" kcms/*/CMakeLists.txt
# 对照制品实际导出目标
llvm-readelf/grep "add_library(KF6::" <kio-pkg>/lib/cmake/KF6KIO/KF6KIOTargets.cmake
# → 只有 KIOCore；kauth 无 policy-gen → 分档处置
```

### 第二步：四档处置 + 共性收尾

- **裁**：about-distro / helpers / usbview（理由见上表）
- **留**：CommandOutputContext 型 17 个
- **改**：samba——`KIOWidgets → Qt6::DBus`（qt_add_dbus_interface 生成
  的接口需要）+ 删 KPropertiesDialog 集成（.h 的 Q_INVOKABLE、.cpp 的
  QApplication include、.ui QML 的 ToolButton 三处联动）
- **守卫**：energy 留上游 `CMAKE_SYSTEM_NAME MATCHES Linux` 后

```cmake
# 顶层 CMakeLists 补丁关键行
find_package(Qt6 ${QT_MIN_VERSION} CONFIG REQUIRED COMPONENTS
    Core Gui Widgets DBus Qml Quick)   # samba DBus 接口 + KCMUtilsQuick 引用 Qt6::Qml

set_target_properties(KInfoCenterInternal PROPERTIES
    VISIBILITY_INLINES_HIDDEN OFF
    SOVERSION 1)                        # 稳定 soname，防 build-tree DT_NEEDED

# 删除 ADD_CUSTOM_TARGET(kinfocenter_link ...) + install(FILES .../kinfocenter)
```

```python
# conanfile.py package() 末尾：签名手段前移到打包期（E077）
for so in walk_package_elves():
    objcopy --remove-section .codesign so
    binary-sign-tool sign -inFile so -outFile so -selfSign 1
```

### 第三步：test_package 用 KPluginFactory 真加载（补偿验证）

无可执行入口的插件集包，消费者测试的三段式：

```cpp
// 1. 真实加载已装插件（systemsettings 同款机制）
const KPluginMetaData meta(pluginDir.filePath("kcm_cpu.so"));
auto result = KPluginFactory::loadFactory(meta);   // dlopen + factory
// 2. 私有库 dlopen + 元对象符号（注意 mangle 长度 20 不是 21）
QLibrary internal(pkgLibDir + "/libKInfoCenterInternal.so.1");
internal.resolve("_ZN20CommandOutputContext16staticMetaObjectE");
// 3. 全量模块清单校验（抓"该装的没装"）
```

这套组合能同时抓出签名（EACCES）、链接（DT_NEEDED 解析）、元数据
（KPluginMetaData isValid）三类问题——只查文件存在一个都抓不到。

## 后备方案（fallback）

- 若下游需要 about-distro：等 kio 发布含 KIOGui 的完整基线后，
  补丁的裁剪行可整段恢复（裁剪点全部是 `add_subdirectory` 行删除，
  git revert 粒度干净）。
- 若 worker 上发现 pkg-config 误探 host 库：本模式的 usbview 裁剪
  是通用防御；恢复时应改用 conan 依赖 + 显式 CMAKE_PREFIX_PATH
  而不是放回 pkg-config 探测。

## 验证构建

- kinfocenter 6.7.2（本 PR）：上游 samba autotests 2/2 Passed
  （ctest 100%），消费者测试 PASSED (0 failures)——
  `conan create --build=missing -pr=default -r=ohpcd` RC=0，
  日志 `~/huawei/kinfocenter-create.log`。
- verify_builds: 待 PR CI 绿后回填构建号。

## 知识协作

- source_pr: 本 PR（交付后回填）
- source_commit: 本 PR HEAD（交付后回填）
