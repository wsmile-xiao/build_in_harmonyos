# ddate — 格里高利历转 Discordian 历日期转换器

## 简介

ddate 是一个幽默风格的命令行工具，将当前日期（或指定日期）转换为 Discordian（Erisian）历法格式输出。
上游为从 util-linux 剥离出的单文件 C 程序（ddate.c），CMake 构建，零外部依赖。

## OpenHarmony 适配要点

- **构建系统**: CMake（单个可执行文件 + gzip 压缩 man 页）
- **版本兼容**: 上游 `cmake_minimum_required(VERSION 2.8)`，CMake 4.x 需 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（知识 E187/E103）
- **无依赖**: 自包含，仅用标准 C 库（stdlib/string/time/stdio）
- **无上游测试**: 发布包无任何测试套件，按 no_tests 口径申报；test_package 提供 6 项内容级功能验证
- **工具包**: package_type=application，已声明 commands.json

## 可用版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 0.2.2 | built | 2026-09-10 | 配方完成，待真机验证 |

## 安装

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- ddate 0.2.2
```

## 使用方法

```bash
ddate                   # 输出当前 Discordian 日期
ddate 1 1 2026          # 转换指定日期（day month year 顺序）
ddate "+%Y" 1 1 2026    # 格式化输出（%A 星期 %B 季节 %d 天 %Y 年）
```

## 示例输出

```
$ ddate 1 1 2026
Sweetmorn, Chaos 1, 3192 YOLD
```
