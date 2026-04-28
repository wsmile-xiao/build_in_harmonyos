# Scintilla

## 简介
Scintilla 是一个跨平台的源代码编辑控件库，广泛用于代码编辑器（如 SciTE、Notepad++ 等）。

## OHOS 适配
- 核心库 33 个源文件零修改编译
- 新增 PlatOHOS.cxx（707行）平台层，使用 HarmonyOS Native Drawing API 实现渲染
- 新增 ScintillaOHOS.cxx Editor 集成层，支持触摸交互、键盘输入、IME
- 双库产出：libscintilla_core.a（静态）+ libscintilla_ohos.so（共享）
- 共享库需要 --whole-archive 链接防止符号丢失
- CJK 字体需使用 HarmonyOS_Sans_SC.ttf
- DevEco 集成通过 NAPI 桥接 ArkTS

## 依赖
- libnative_drawing.so（HarmonyOS SDK）
- 标准库（C++17）

## 排除与替代
- 不使用 PlatGTK.cxx（需要 GTK）
- 不使用 libraryname 模式（SIGSEGV 问题）
- 使用 SurfaceHolder 模式替代

## 功能验证
- 52/52 单元测试通过（3791 个断言）
- 设备测试：文字显示、光标闪烁、触摸定位、键盘输入、IME 中文输入均通过

## 参考
- 官网：https://www.scintilla.org/
