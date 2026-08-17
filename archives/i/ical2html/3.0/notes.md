# ical2html 3.0 HarmonyOS 适配说明

## 构建说明

ical2html 3.0 使用 Autotools 构建，上游依赖 libical。本适配内置构建 libical 3.0.8，并使用 HarmonyOS aarch64 Clang 工具链完成编译。

## HarmonyOS 适配

- 使用 HarmonyOS Clang/Clang++ 编译。
- 为旧版 libical 增加 CMake policy 兼容参数。
- 处理 HarmonyOS 环境中失效的默认编译器和 Shell 路径。
- 绕过当前文件系统下 Autoconf `mktemp -d` 临时目录权限异常。
- 修复 `getopt_long()` 返回值使用 `char` 接收导致参数解析异常的问题，将相关变量调整为 `int`。

## 构建产物

- `ical2html`
- `icalfilter`
- `icalmerge`

## 测试

`test_package` 使用示例 iCalendar 文件运行打包后的 `ical2html`，验证：

- 程序正常退出。
- 成功解析日历事件。
- 输出包含预期事件内容。
- 输出为 HTML 日历内容。

本地 CI 结果：

- L0: pass
- L1: pass
- L4: pass
- L5: pass
- Build Summary: 1 success / 0 failed
