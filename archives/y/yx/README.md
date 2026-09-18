# yx

> YAML Data Extraction Tool — 按 key / 序列索引路径从 YAML 文档中提取目标数据

## 基本信息

| 项目 | 内容 |
|------|------|
| 上游版本 | 1.0.2 |
| 许可证 | MIT |
| 主页 | https://gitlab.com/tomalok/yx |
| 源码 | https://gitlab.com/tomalok/yx/-/archive/1.0.2/yx-1.0.2.tar.gz |
| 构建系统 | makefile（纯 Makefile，单文件 C 实现） |
| 依赖 | libyaml/0.2.5（静态链接） |

## 描述

`yx` 是一个小型命令行工具，用于从 YAML 文档中沿 key 路径 / 序列索引路径提取目标数据。
例如 `yx foo bar blah` 从嵌套映射中提取 `foo.bar.blah` 的值；`yx 2` 取出序列的第 2 个元素。

```sh
printf 'foo:\n  bar:\n    blah: three\n' | yx foo bar blah   # => three
printf -- '- one\n- two\n- three\n' | yx 2                    # => two
```

## 支持版本

| 版本 | 状态 | 构建系统 |
|------|------|---------|
| 1.0.2 | built | makefile |

## 命令行工具

安装后提供可执行文件 `yx` 与 man page `yx.1`；命令行声明见同目录 `commands.json`。

## 适配说明

HarmonyOS PC（arm64，`aarch64-linux-ohos` / clang 15）适配要点见 `1.0.2/notes.md`：
上游 Makefile 硬编码 `cc` 且无 CC/CFLAGS 注入点，配方在 `build()` 内以 profile 编译器复现同一编译规则；
`install -s`（strip）在 OHOS 不可复现（ELF `.codesign` 段重写后 execve EACCES），`package()` 原样安装签名二进制。无补丁。
