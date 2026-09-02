# barrier

barrier 是一款开源的键盘鼠标共享（KVM）软件，允许在两台或多台计算机之间共享一套键盘和鼠标，源自 Synergy 1.9 的延续分支。

本仓库归档 **OpenHarmony PC (OHOS armv8) 适配** 的 barrier 2.4.0。

- 上游仓库：https://github.com/debauchee/barrier
- 许可证：GPLv2
- 构建系统：CMake
- 适配方向：**BARRIER_BUILD_GUI=OFF**（CLI 核心 `barriers` / `barrierc`）

## 适配说明（OHOS）

本适配以 CLI 核心（服务端 `barriers` + 客户端 `barrierc`）为交付目标，覆盖 KVM
键鼠共享主功能。Qt5 GUI 为已知限制（ohpcd `qt5-qtbase/5.15.2` 二进制为 `-no-widgets`，
不暴露 `Qt5::Widgets`，GUI 无法链接）。

关键 OHOS 适配点见档案目录下的 `notes.md` 与 `manifest.yaml`。

## 版本

- 2.4.0 — CLI 核心 OHOS armv8 适配（已构建）
