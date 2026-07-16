# GNU UnRTF

> GNU UnRTF converts Rich Text Format documents to HTML, text, LaTeX and other formats.

## 简介

GNU UnRTF 是 GNU 项目的命令行工具，可将 RTF 文档转换为 HTML、纯文本、LaTeX、PostScript 等格式。

## OHOS 适配要点

1. 上游 `config/config.guess` 无法识别 `HarmonyOS`，Conan 配方在构建前补充 `HarmonyOS -> *-linux-ohos` 识别逻辑。
2. 上游 `config/config.sub` 不接受 `linux-ohos` OS triplet，Conan 配方在构建前补充 `linux-ohos*`。
3. HarmonyOS/HMDFS 环境下 GNU make jobserver 可能创建 FIFO 失败，构建与安装使用 `-j1`。
4. unrtf 是命令行工具，软件级目录提供 `commands.json`。

## 依赖

无外部 Conan 依赖。

## 验证

`test_package` 会运行：

```bash
unrtf --version
unrtf --text sample.rtf
```
