# detox

`detox` 是一个用于清理文件名的命令行工具。它可以将空格和其他不便于 shell
处理的字符转换为安全形式，并支持按配置文件和转换表定制处理序列。

- 上游项目：https://github.com/dharple/detox
- 许可证：BSD-3-Clause
- 构建系统：Autotools
- Conan 包：`detox/3.0.1`

## 包含的命令

| 命令 | 用途 |
| --- | --- |
| `detox` | 清理文件和目录名称，支持预演与递归处理 |
| `inline-detox` | 从标准输入或文件读取文本并输出清理后的内容 |

## HarmonyOS 适配

HarmonyOS 版本使用官方 3.0.1 Release 源码和 Conan 构建。原生构建执行完整上游
测试；交叉构建会生成全部 Check 单元测试程序，再送到目标机执行。测试夹具通过
`TMPDIR` 使用 HarmonyOS 可写临时目录，不改变程序本身的跨平台行为。包消费测试
另外验证 `/data/local/tmp` 下的实际文件重命名。

具体构建和测试结果见 `3.0.1/notes.md` 与 `3.0.1/reports/`。
