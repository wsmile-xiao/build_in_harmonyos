# KWStyle - Kitware Style Checker

## 简介

KWStyle 是 [Kitware](https://www.kitware.com/) 官方的**源码风格检查器**，用于在多人
协作的软件流程中强制保持代码风格一致：缩进、版权头注释、最大行长、封装完整性、
内部变量命名、语句/变量分行、文件末尾换行等。它采用 Kitware BSD 式许可（见
`Copyright.txt`），也是 ITK / VTK 等大型项目长期使用的风格门禁工具。

- 上游仓库：<https://github.com/Kitware/KWStyle>
- 规则说明：<https://kitware.github.io/KWStyle/resources/features.html>

## OHOS 适配

本包适配到 HarmonyOS PC（aarch64），要点：

| 项 | 说明 |
|---|---|
| 构建系统 | 上游 CMake（>= 3.10.2），静态构建（R26） |
| 外部依赖 | **零** —— 上游无任何 `find_package`，vendored KWSys 随源码编译 |
| 测试 | 上游自带 CTest 共 41 项（6 单测 + 35 bug 基线对比），实测 41/41 通过 |
| 产物 | `bin/KWStyle` 命令行工具 |

## 使用方法

```bash
# 查看版本（注意：上游用单横线选项，不是 --version）
KWStyle -version

# 查看可用选项
KWStyle -h

# 用规则文件检查单个文件
KWStyle -xml rules.kws.xml -exportxml report.xml path/to/file.cxx

# 递归检查整个目录
KWStyle -d src -R -xml rules.kws.xml -exportxml report.xml

# 以 GCC / VIM / MSVC 格式输出便于编辑器跳转
KWStyle -gcc -xml rules.kws.xml path/to/file.cxx
```

规则文件为 XML，例如禁用 Tab 并把最大行长设为 120：

```xml
<?xml version="1.0" encoding="iso-8859-1"?>
<Description>
<LineLength>120</LineLength>
<Tabs>1</Tabs>
</Description>
```

退出码语义：检出错误时返回非 0，风格干净时返回 0（便于接入 CI 门禁）。

## 许可证

上游根目录无 `LICENSE`，唯一许可证文件为 `Copyright.txt`（Kitware BSD 式许可，
SPDX 归为 `BSD-3-Clause`）。产品源码中根目录 38 个 `.cxx`/`.h` 标注
"See Copyright.txt"；`metaCommand.cxx` / `metaCommand.h` 带 Apache-2.0 头
（Copyright NumFOCUS）且被编入 `bin/KWStyle`；另外随包安装的
`share/KWStyle/headers/ITKHeader.h` 同为 Apache-2.0（`VTKHeader.h` 为 Kitware BSD 式）；
随源码 vendored 的 boost 头为 `BSL-1.0`。

本包整体按复合 SPDX 声明：**`BSD-3-Clause AND Apache-2.0 AND BSL-1.0`**。
依据与核对时间见 `1.1.0-git20250114.eb1e46d/notes.md` §9。
