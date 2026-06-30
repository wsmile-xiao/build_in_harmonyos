# hebcal

## 简介

hebcal是一个犹太万年历程序，用于计算和显示犹太历法中的重要日期和事件。

## 功能

- 显示希伯来日期
- 犹太节日（包括Yom Ha'atzmaut和Yom HaShoah等）
- 每周的Sedrah（ Torah段落）
- Omer天数计数
- 日落时间计算
- 多语言支持（英语、希伯来语、德语、法语等）

## 版本历史

- **4.31** (2022-08-16): 当前稳定版本
  - 支持多种语言翻译
  - 改进的日落计算算法
  - 兼容OpenHarmony平台

## 构建系统

- **类型**: autotools（需要手动创建Makefile）
- **编译器**: clang
- **依赖**: 无外部依赖

## 平台适配说明

在OpenHarmony平台上，由于HMDFS文件系统的特殊限制：
- configure脚本无法创建临时文件，需要手动创建Makefile
- 需要手动生成config.h和翻译文件（strings_*.c）
- 已生成16个补丁文件用于平台适配

## 安装

通过cmd-pkgs安装预编译包：
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- hebcal 4.31
```

## 使用示例

```bash
# 显示当前年份的犹太历
hebcal

# 显示2024年的犹太历
hebcal 2024

# 显示2024年1月的犹太历
hebcal 1 2024

# 仅显示Omer天数
hebcal -ho

# 显示版本
hebcal --version
```

## 许可证

GPL-2.0-or-later

## 更多信息

- 源码仓库: https://github.com/hebcal/hebcal
- 文档: https://github.com/hebcal/hebcal/blob/master/README.md