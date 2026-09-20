# kmousetool

kmousetool 是 KDE 无障碍（accessibility）工具集的自动点击器：用户按住鼠标键一段时间
（或按下空格/回车等修饰键）后，工具通过 XTest 扩展自动合成真实的鼠标点击，帮助
运动障碍、震颤或单手操作的用户免于反复手动点击。它是一个 Qt Widgets 图形界面应用，
驻留系统托盘（KStatusNotifierItem）。

- 上游：https://apps.kde.org/kmousetool/ （KDE Gear，随 release-service 发布）
- 源码：https://download.kde.org/stable/release-service/26.04.0/src/kmousetool-26.04.0.tar.xz
- 版本：26.04.0（首次适配，上游版本号）
- 构建系统：CMake（KDE ECM 标准布局）

## OHOS PC 适配要点

- **CMake 系统名**：本机 cmake 4.1.2 无 HarmonyOS 平台模块，system=HarmonyOS 时
  `UNIX=FALSE`，FindX11 等 `if(UNIX)` 守卫的模块整体静默跳过；toolchain 设
  `CMAKE_SYSTEM_NAME=Linux` 修复（OHOS 即 Linux 内核）。
- **X11 依赖裁剪**：上游 CMakeLists 硬检查 libXt（Xt Intrinsics），但源码并未使用
  任何 Xt 符号——补丁 0001 删除该检查；补丁 0002 删除 5 个死 include
  （Intrinsic.h/StringDefs.h/xtestext1.h 仅 libXt 提供、fixx11h.h 为 kdelibs 遗留头，
  全仓无包提供）。实际 X 依赖只剩 libX11（XOpenDisplay）+ libXtst（XTest API）。
- **托盘图标**：KStatusNotifierItem 由 statusnotifieritem/6.26.0 包提供
  （kstatusnotifieritem 包不存在，勿按上游 find_package 名称想当然）。
- **KF6DocTools**：可选组件，OHOS 无 gettext/msgfmt，KF_SKIP_PO_PROCESSING=ON 跳过
  手册页处理。
- **test_package**：开发机对工具链构建的 GUI 应用 ELF 执行一律 EPERM（与大小/PIE/
  RUNPATH 无关的系统管控），故按 actiona 先例做产物契约断言（ELF/aarch64 魔数、
  DT_NEEDED 链接集、XTestFakeButtonEvent 重定位），并编译运行 xtest_smoke 真实验证
  被测包暴露的 XTest API。

## 依赖

qtbase/6.11.1.1（DBus 变体）、qtmultimedia/6.11.1、KF6 全家桶（kconfig/kconfigwidgets/
kcoreaddons/kcrash/ki18n/kiconthemes/kwidgetsaddons/kxmlgui 6.18.0 + kdbusaddons 6.29.0）、
statusnotifieritem/6.26.0、libx11/1.8.13、libxtst/1.2.5、extra-cmake-modules/6.29.0。

## 使用

```bash
conan install -r ohpcd --requires=kmousetool/26.04.0 -pr:h <ohos-profile>
# 或 conan create 本目录配方
kmousetool   # Qt6 + KF6 图形界面应用，需图形会话
```
