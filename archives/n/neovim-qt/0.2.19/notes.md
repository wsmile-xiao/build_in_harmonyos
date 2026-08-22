# neovim-qt 0.2.19 适配笔记

## 项目简介
neovim-qt—— Neovim 的 Qt5 GUI 前端（C++，CMake 构建，ISC 许可），提供
libneovim-qt 客户端库 + nvim-qt GUI 可执行文件。上游 equalsraf/neovim-qt。

## 依赖与制品仓
- **qt5-qtbase/5.15.2**（Gui/Network/Widgets，制品仓已发布）✅
- **qt5-qtsvg/5.15.2**（制品仓已发布）✅
- **msgpack-c/7.0.0**（USE_SYSTEM_MSGPACK=ON，避免上游 bundled；制品仓已发布）✅
- **neovim/0.11.3**（tool 依赖，运行时；制品仓已发布）✅

## OHOS 适配要点
1. **CMake 构建**：`USE_SYSTEM_MSGPACK=ON` + `WITH_QT=Qt5` +
   `REPRODUCIBLE_BUILD=ON`；
2. **offscreen 测试**：鸿蒙无 X11/Wayland 显示服务器，测试用
   `QT_QPA_PLATFORM=offscreen` 规避 xcb 错误（Homebrew 测试先例
   QT_QPA_PLATFORM=minimal 同理）；
3. **依赖全在制品仓**：本库适配可行（编译 + offscreen 验证）。

## 验证
- 模拟 CI 干净 PATH conan create（--build=missing, ohos-aarch64 profile）；
- test_package：QT_QPA_PLATFORM=offscreen 运行 nvim-qt --version。
