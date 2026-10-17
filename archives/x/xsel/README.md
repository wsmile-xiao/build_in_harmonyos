# xsel

X selection 命令行操作工具，用于获取和设置 X 剪贴板（PRIMARY / SECONDARY / CLIPBOARD selection）内容。

## 功能

- 读取当前 selection 内容到标准输出
- 从标准输入设置 selection 内容
- 支持 append / follow / clear / delete / exchange / keep 等操作
- 支持 --primary / --secondary / --clipboard 三种 selection 类型

## 编译版本

- **1.2.1** (2026-08-14): HarmonyOS 平台适配版本

## OHOS 适配

- GitHub tag archive 不含预生成 configure，构建时 `autoreconf -fi` 自举
- X11 依赖（libX11）来自 cmd-pkgs 预编译包，非 conan 依赖
- 上游无自动化测试套件（已审计），由 test_package 冒烟验证

## 依赖

- libX11（cmd-pkgs 预编译包）

## 参考资料

- 上游仓库: https://github.com/kfish/xsel
- 官方主页: https://vergenet.net/~conrad/software/xsel/
