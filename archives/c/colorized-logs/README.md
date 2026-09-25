# colorized-logs

colorized-logs 是 kilobyte 维护的终端输出处理工具集，用于把 ANSI 彩色终端输出
在"彩色 <-> 纯文本 <-> HTML"之间转换，以及回放 ttyrec 录屏、通过伪终端运行命令。

## 工具

- `ansi2html` — ANSI 彩色文本转 HTML（含 `<pre>` 块与颜色样式）
- `ansi2txt` — 剥离 ANSI 转义序列，输出纯文本
- `ttyrec2ansi` — 把 ttyrec 录屏字节流重放为带 ANSI 的终端输出
- `pipetty` / `lesstty` — 在伪终端（pty）中运行命令并保留 isatty 语义

## HarmonyOS 适配要点

- 纯 C 实现，CMake 构建，无第三方依赖（仅链接系统 util 库的 openpty）
- 适配版本：2.7（见 `archives/c/colorized-logs/2.7/`）
- 上游测试（ctest 5 项）全量通过；`test_package/` 提供消费者验证，
  `test_ohos/` 提供 aarch64 ELF / ANSI 解码往返 / ttyrec 重放 / pty 分配等鸿蒙专项检查
