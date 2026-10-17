# kinfocenter 6.7.2 — HarmonyOS PC (OHOS aarch64) 适配笔记

## 概况

- 上游：KDE Plasma 6.7.2 kinfocenter（`https://invent.kde.org/plasma/kinfocenter`）
- 源码：`https://download.kde.org/stable/plasma/6.7.2/kinfocenter-6.7.2.tar.xz`（sha256 `a28f42d1f6f8b36ff1f551d593e21165098a976af91fe718c37edde0113a407d`）
- 注：任务卡给的 release-service 目录 404（kinfocenter 属 Plasma 线而非 Gear 线），实测官方 plasma 目录可达，conandata 采用实测 URL。
- 包形态：**library**（KCM 插件集）。上游 kinfocenter"可执行文件"是指向 systemsettings 的符号链接，OHOS 包集无 systemsettings——符号链接及其 install 规则裁除；payload = `lib/plugins/plasma/kcms/kinfocenter/*.so`（18 个 KCM 插件）+ `lib/libKInfoCenterInternal.so.1`（私有 QML helper 库）+ categories/desktop 元数据。

## 依赖线（KF6 6.26 closure，与 kcmutils/6.26.0 严格对齐）

- `qtbase-sql-dbus/6.11.1`：Qt6 DBus 模块 + qdbusxml2cpp（samba kcm 的 qt_add_dbus_interface 需要；kwalletmanager 26.04.0 先例——KF6 6.26 制品的 qtbase/6.11.1 天然锚与之共存，不动任何 package id）
- `qtdeclarative/6.11.1`：Qml/Quick 组件 + qml 工具链（KInfoCenterInternal 是 ecm_add_qml_module + GENERATE_PLUGIN_SOURCE 的 QML 模块）
- `kcmutils/6.26.0`：kcmutils_add_qml_kcm 宏 + KCMUtilsQuick（拖入 kio/kxmlgui/kitemviews + kconfigwidgets 6.18 + KF6 6.26 override 全套）
- `kio/6.26.0`：KIOCore（KSambaShare/KSambaShareData 符号实核在 KIOCORE_ONLY 基线制品内）
- `kservice/solid/kauth 6.26.0`：顶层 find_package(KF6 ...) 组件
- `ecm/6.26.0`（build tool）

依赖图探针（conan install --build=never -r=ohpcd）31/31 全部解析为已发布二进制，零源码构建。

## OHOS 裁剪（patches/0001-ohos-trim-kcms.patch，7 文件）

| 模块 | 处置 | 理由 |
|------|------|------|
| about-distro | 裁 | 唯一 libdrm(pkg_check_modules)/UDev/vulkan+opengl helper/KIOGui 消费者，OHOS 包集全缺（kio=KIOCORE_ONLY 基线） |
| helpers (dmidecode-helper) | 裁 | kauth OHOS 包 FAKE 后端，无 kauth-policy-gen host 工具供 KAUTH_INSTALL_* 安装宏执行 |
| usbview | 裁 | FindUSB1 经 pkg-config 探测，worker 间解析不一致（可能链进 x86_64 host 库），确定性风险 |
| energy | 上游 Linux 守卫天然跳过 | CMAKE_SYSTEM_NAME=OHOS 不匹配 |
| samba | 改造 | KIOWidgets→Qt6::DBus + KPropertiesDialog 集成移除（KIOCORE_ONLY 基线）；上游 autotests 保留真跑 |
| kinfocenter symlink | 裁 | systemsettings 不在包集，悬空符号链接无法 install |
| KInfoCenterInternal | 加 SOVERSION 1 | 无 soname 时已装插件记录 build-tree DT_NEEDED；稳定引用 libKInfoCenterInternal.so.1 |
| Qt6 find_package | +DBus/Qml/Quick | samba DBus 接口生成 + KCMUtilsQuick 接口目标需要显式组件创建 |

保留 18 个 KCM：audio_information/block_devices/cpu/edid/egl/firmware_security/glx/interrupts/kwinsupportinfo/memory/network/opencl/pci/samba/sensors/vulkan/wayland/xserver（全部 CommandOutputContext 型 + samba 双模型型，链接 KCMUtilsQuick/CoreAddons/I18n/KInfoCenterInternal 闭环可用）。

## 测试统计（申报口径）

- **上游注册测试数 N = 3**：kcms/samba/autotests 的 2 个 ecm_add_tests（ksambasharemodeltest、smbmountmodeltest）+ appiumtests 的 1 个 add_test（kinfocenter_appiumtests）。
- **实际执行 2 个**（BUILD_TESTING=ON + ctest）：ksambasharemodeltest、smbmountmodeltest——链接 kcm_samba_static（QAbstractItemModelTester 驱动 KSambaShareModel/SmbMountModel 两模型）。
- **豁免 1 个**：kinfocenter_appiumtests——appiumtests/CMakeLists.txt 的 Linux 守卫 + SeleniumWebDriverATSPI（GUI 全会话 + AT-SPI 无障碍栈）在 OHOS 交叉环境不存在，非 Linux CI 不注册不执行。
- test_package（消费者测试，鸿蒙特有）：1/1（KPluginFactory::loadFactory 真实加载已装 kcm_cpu 插件 + dlopen libKInfoCenterInternal.so.1 解析 CommandOutputContext 元对象 + 18 模块安装集全验）。

### 上游测试通过情况（本机 arm64 OHOS 实测，conan create 内 ctest）

```
100% tests passed, 0 tests failed out of 2
Total Test time (real) = 0.36 sec
```

- ksambasharemodeltest：**Passed**（QAbstractItemModelTester 驱动 KSambaShareModel 全模型协议）
- smbmountmodeltest：**Passed**（同款驱动 SmbMountModel）
- 运行环境：QT_QPA_PLATFORM=offscreen、隔离 HOME/XDG_* 沙箱、KF6 相对 DT_NEEDED 兼容链接（../bin、../../bin 双深度）+ 绝对 DT_NEEDED stub 修复（kcmutils 6.26.0 先例手段）。

test_package 消费者测试（鸿蒙特有）：**PASSED (0 failures)**——KPluginFactory::loadFactory 真实加载已装 kcm_cpu 插件（systemsettings 同款机制）+ dlopen libKInfoCenterInternal.so.1 解析 CommandOutputContext::staticMetaObject（注意 mangle 长度 _ZN20）+ 18 KCM 模块安装集全验。payload 在 package() 期统一重签（llvm-objcopy --remove-section .codesign + binary-sign-tool -selfSign，E077 手段前移），消费者环境零依赖。

## 关键坑与先例引用

- KGOLDRUNNER 26.04.0：KF_IGNORE_PLATFORM_CHECK / KF_SKIP_PO_PROCESSING / cmake paths 手写 / build env LD_LIBRARY_PATH
- KCMUTILS 6.26.0：_bake_needed_path_stubs（绝对 DT_NEEDED stub 修复）+ _prepare_ctest_runtime_links（相对 DT_NEEDED 兼容布局）——本配方全量复用
- QQC2-BREEZE-STYLE 6.7.5（同账号 Plasma 6.7 线最近亲）：OHOS shared-library soname rules（CMAKE_USER_MAKE_RULES_OVERRIDE）+ QT_ADDITIONAL_PACKAGES_PREFIX_PATH
- KIO 6.26.0：KIOCORE_ONLY 基线边界（KIOWidgets/KIOGui/KSambaShare 归属核验——KSambaShare 实测在 KIOCore）

## 本地构建证据

- conan create（arm64 OHOS 真机）：构建 + ctest + test_package 全链执行，日志落盘 `~/huawei/kinfocenter-build/logs/`
