# aha — ANSI HTML Adapter

## 软件简介

aha是一个将ANSI终端颜色代码转换为HTML的工具。它可以将包含ANSI/VT100控制序列的文本转换为符合W3C标准的HTML文档。

**主要功能**:
- 将ANSI颜色代码转换为HTML样式
- 支持标准颜色、亮色、背景色等
- 生成符合W3C标准的XHTML文档
- 支持管道输入和文件输入

## 已编译版本

| 版本 | 状态 | 编译日期 | 补丁数 |
|------|------|----------|--------|
| 0.5.1 | built ✅ | 2026-07-15 | 1 |

## 使用方法

### 基本用法

```bash
# 管道输入（实时转换）
echo -e '\033[31m红色文本\033[0m' | aha > output.html

# 文件输入（转换日志文件）
aha -f colored-log.txt > output.html

# 指定标题和样式
echo -e '\033[32m绿色\033[0m' | aha --title "我的日志" --stylesheet > output.html
```

### 常见选项

- `--black, -b`: 黑底白字配色
- `--pink, -p`: 粉色背景
- `--stylesheet, -s`: 使用CSS样式表代替内联样式
- `--title X, -t X`: 设置HTML标题
- `--lang X, -L X`: 设置语言代码
- `--word-wrap, -w`: 自动换行

## 平台适配说明

### 鸿蒙系统适配

**编译补丁**:
1. `0001-Makefile.patch`: 替换install命令为mkdir/cp/chmod组合
   - 原因: 鸿蒙系统缺少GNU install命令

**编译依赖**: 无

**构建系统**: makefile（手动Makefile）

## 验证结果

### 功能测试

| 测试项 | 结果 |
|--------|------|
| 版本显示 | ✅ 通过 |
| 帮助信息 | ✅ 通过 |
| ANSI转HTML转换 | ✅ 通过 |
| 预编译包执行 | ✅ 通过 |

### 质量门禁

| 门禁项 | 结果 |
|--------|------|
| G0 干净构建验证 | ✅ 通过 |
| G1 二进制完整性 | ✅ 通过 |
| G2 功能可用性 | ✅ 通过 |
| G3 可移植性 | ✅ 通过 |
| G4 档案完整性 | ⚠️ 部分 |

## 获取预编译包

预编译包已发布到cmd-pkgs仓库，可通过以下方式安装：

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- aha 0.5.1
```

安装后路径: `~/usr/local/bin/aha`

## 源码信息

- **源码地址**: https://github.com/theZiz/aha
- **许可证**: LGPL-2.1+ / MPL-1.1
- **维护者**: theZiz

## 相关资源

- [GitHub仓库](https://github.com/theZiz/aha)
- [编译详情](./0.5.1/notes.md)
- [测试报告](./0.5.1/reports/test-report.md)
