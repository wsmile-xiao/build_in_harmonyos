# FTXUI

## 简介
FTXUI 是一个 C++ 功能式终端用户界面库，用于构建终端应用程序。提供组件（component）、DOM 和屏幕（screen）三层抽象，支持鼠标、键盘事件处理。

## OHOS 适配
- **纯 header-only + static library**: 无外部依赖，编译简单
- **CMake 平台检测**: CMake 检测到 HarmonyOS 但不影响编译
- **测试跳过**: googletest FetchContent 有 git safe directory 问题，需跳过测试 (`-DFTXUI_BUILD_TESTS=OFF`)
- 需要 pthread（已找到）

## 依赖
- 编译工具: clang, cmake
- pthread（系统提供）

## 构建产物
- libftxui-screen.a (屏幕渲染)
- libftxui-dom.a (DOM 元素)
- libftxui-component.a (交互组件)
- 链接顺序: ftxui-component → ftxui-dom → ftxui-screen

## 功能验证
```bash
# 检查库文件
ls -la $HOME/usr/local/lib/libftxui-*.a
pkg-config --modversion ftxui
```

## 参考
- GitHub: https://github.com/ArthurSonzogni/FTXUI
- 源码: https://github.com/ArthurSonzogni/FTXUI/archive/refs/tags/v6.1.9.tar.gz
