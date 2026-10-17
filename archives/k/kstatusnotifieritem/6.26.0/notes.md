# kstatusnotifieritem 6.26.0 适配笔记

## Scope

kstatusnotifieritem 是 KDE Frameworks 6 的系统托盘（freedesktop
StatusNotifierItem 规范）库（libKF6StatusNotifierItem），是 kteatime 等
KDE Gear 应用的硬依赖。ohpcd 制品仓此前未发布该包，按 R36 依赖优先原则
先行适配本包。

## 上游测试三步法（R51）

1. 清点：上游 tests/ 目录 1 个测试目标（tests/kstatusnotifieritemtest，
   120 行，QApplication 交互式 demo），未注册 add_test/ctest；无
   autotests 目录。
2. 运行：BUILD_TESTING=ON 在真机构建该目标，QT_QPA_PLATFORM=offscreen
   下以 8s timeout 运行 —— 正常进入事件循环并存活（rc=124 视为通过，
   任何更早非零退出视为崩溃失败）。实测 1/1 通过。
3. 回填：实测数 1 / 通过数 1 / 通过率 100%。说明：该测试 main() 以
   app.exec() 结束且无断言注册，无法无超时直接运行，采用启动稳定性
   检查口径（详见 manifest.yaml / test_package/MANIFEST.yml）。

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` 绕过 KDE 平台白名单检测。
- `WITHOUT_X11=ON`：OHOS 无 X11，跳过 find_package(X11)（HAVE_X11=0）。
- `USE_DBUS=OFF`：ohpcd qtbase 以 FEATURE_dbus=OFF 构建，无 Qt6::DBus；
  上游所有 DBus 路径均以 `#if HAVE_DBUS` 干净编译排除，无需源码改动。
- `BUILD_PYTHON_BINDINGS=OFF`：无 Shiboken6/PySide6。
- 补丁 0001-disable-po-qm-processing.patch：注释
  `ecm_install_po_files_as_qm(poqm)` 与
  `ecm_create_qm_loader(...)`，二者需要 Qt6LinguistTools（ohpcd 未发布），
  沿用 kconfig/6.26.0 同口径。
- ECM_MODULE_PATH 手工注入（CMakeDeps 生成的 ECMConfig.cmake 不传播该
  变量），同 kguiaddons/6.26.0 模式。

## Verification

- 源码 SHA256：`898914c94820f99889d879f33cabbb5fbe7b9f4e24a6a1d9a9b4439489bc3266`
- 依赖：qtbase/6.11.1、kwindowsystem/6.26.0（均已在 ohpcd 发布，
  conan download 实测）；tool_requires ecm/6.26.0。
- 上游测试：1/1 通过（offscreen 启动稳定性）。
- test_package：链接 KF6::StatusNotifierItem，5 项断言（id 默认状态
  Passive / setStatus 往返 / setCategory / setTitle）。

## Notes

- kteatime 后续适配直接 `self.requires("kstatusnotifieritem/6.26.0")`。
- 本包为库类型（package_type=library），无 commands.json（R38 不适用）。
---

**编译结束**: 2026-09-20 12:19
**最终状态**: built
