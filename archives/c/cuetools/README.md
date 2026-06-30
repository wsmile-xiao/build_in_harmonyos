# cuetools

CUE 文件处理工具集，用于处理 CD 镜像的 CUE/BIN 文件。

## 软件信息

- **官网**: https://www.nongnu.org/cuetools/
- **源码**: https://github.com/svend/cuetools
- **版本**: 1.4.1
- **许可**: GPL-2.0

## 工具列表

- **cuebreakpoints**: 输出 CUE 文件中的断点信息
- **cueconvert**: 转换 CUE 文件格式
- **cueprint**: 打印 CUE 文件信息
- **cuetag**: 标记工具（Shell 脚本）

## 编译状态

| 版本 | 状态 | 构建系统 | 编译日期 |
|------|------|---------|---------|
| 1.4.1 | built | autotools | 2026-06-04 |

## 依赖

无外部依赖。

## 安装

通过 cmd-pkgs 公共安装脚本：

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- cuetools 1.4.1
```

## 验证

```bash
cuebreakpoints --version
cueconvert --version
cueprint --version
```

输出：`cuetools 1.4.0`

## 注意事项

- 版本号显示为 1.4.0，这是软件本身的行为，实际编译的是 1.4.1 tag
- 所有工具均为 ELF 64-bit aarch64 动态链接可执行文件
- cuetag.sh 是 Shell 脚本，需要 sh/bash 解释器

## 详细编译信息

详见 [1.4.1/notes.md](./1.4.1/notes.md)