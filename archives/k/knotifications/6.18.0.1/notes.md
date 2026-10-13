# knotifications 6.18.0.1 notes

## 修订原因（相对 6.18.0）

- 已发布的 `knotifications/6.18.0` 只提供 **static** 变体（`default_options = {"shared": False}`）且未编 PIC；
  而它的消费者 `kjobwidgets/6.18.0` 是 **shared** 且直接 `requires("knotifications/6.18.0")`。
  于是任何"从源码重建 kjobwidgets"的图都会把 `libKF6Notifications.a` 链进 `libKF6JobWidgets.so`，报：
  `ld.lld: error: relocation R_AARCH64_ADD_ABS_LO12_NC cannot be used against symbol '...'; recompile with -fPIC`
- 本修订在 `generate()` 增加 `tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON"`：静态库带 PIC 后既能被静态消费者使用，
  也能被 shared 消费者链接，**对静态消费者没有行为变化**。
- **依赖 pin 有意保持不变**（`qtbase/6.11.1`、`kconfig/6.18.0`、`kcoreaddons/6.18.0`、`ki18n/6.18.0`）：
  现有消费者（如 `kjobwidgets/6.18.0`）仍钉这些版本，若本修订提版到 `.1`/`.2` 会在其图中形成同包双版本（`Version conflict`）。
- `conandata.yml` 的 `patches` 键同步为 `"6.18.0.1"`（键未同步会导致补丁静默不生效）。
- **新增打包期签名**（`package()` 调用 `_sign_ohos_package_elfs()`）：OHOS 只加载带有效 `.codesign` 段的 ELF，
  而本配方原先没有任何签名步骤 ⇒ **shared 变体构建出来的 `libKF6Notifications.so.6` 在消费者运行时无法加载**，
  实测表现为 kjobwidgets 的上游测试报 `Error loading shared library libKF6Notifications.so.6`。
  现在打包后对包内所有 ELF 先 `llvm-objcopy --remove-section .codesign` 再
  `binary-sign-tool sign -selfSign 1`，并 `chmod 755`（与 ktextaddons/libkleo/kjobwidgets 等配方的做法一致）。

## Scope

This recipe upgrades KNotifications to the 6.18.0 framework level required by
KJobWidgets 6.18.0.

## Adaptations

- DBus and Canberra notification backends are disabled for the current OHOS
  baseline.
- Python bindings and translation catalog generation are disabled.
- **Position independent code is forced on** so that the static archive can be
  linked into shared libraries (KJobWidgets 6.18.0 defaults to `shared=True`).

## Verification

- 2026-10-11 real device (`10.195.180.238:2222`) `conan create archives/k/knotifications/6.18.0.1`:
  exit code 0, `test_package` 1/1 passed (static 变体).
- 2026-10-11 real device 同一命令加 `-o knotifications/*:shared=True`（shared 变体，验证签名路径）：
  exit code 0，日志出现 `Signed 1 OHOS package ELF file(s)`，`Created package revision 7912f04f…`，
  `test_package` **1/1** 通过（消费者运行时成功加载签名后的 `libKF6Notifications.so.6`）。
- End-to-end check (device-side `[replace_requires] knotifications/*: knotifications/6.18.0.1`,
  no other repository file touched): the `kjobwidgets/6.18.0` `-fPIC` link failure disappeared and the
  build progressed into `kio/6.18.0` itself (204 compiled targets).
- Earlier 6.18.0 notes: local pre-PR checks on 2026-08-31 (`py_compile`, `conan export`) passed.
