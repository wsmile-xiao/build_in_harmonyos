# fortune

## 简介
fortune 是著名的电子 fortune-cookie 生成器，随机显示有趣的语录、名言或幽默文本。

## 基本信息
- **软件名**：fortune-mod
- **版本**：9708
- **描述**：Infamous electronic fortune-cookie generator
- **构建系统**：Makefile（无 configure）
- **源码 URL**：https://www.ibiblio.org/pub/linux/games/amusements/fortune/fortune-mod-9708.tar.gz

## 编译版本

| 版本 | 状态 | 编译日期 | 补丁数 |
|------|------|---------|--------|
| 9708 | published | 2026-05-19 | 1 |

## 依赖

无外部依赖（仅需要标准 C 库和 POSIX regex 支持）。

## 编译要点

1. **构建系统**：直接使用 Makefile，无 configure 脚本
2. **编译器**：clang（需要 POSIX regex 支持）
3. **关键修改**：
   - 使用 POSIX regex 替代 BSD regex（REGEXDEFS=-DPOSIX_REGEX）
   - 添加 DESTDIR 支持
   - 禁用 offensive 内容编译

## 安装位置

- fortune 程序：`/usr/local/games/fortune`
- 工具：`/usr/local/bin/strfile`, `/usr/local/bin/unstr`
- 数据文件：`/usr/local/share/games/fortunes/`
- Man 页面：`/usr/local/share/man/man6/fortune.6`, `/usr/local/share/man/man1/strfile.1`

## 使用示例

```bash
# 显示一条随机语录
fortune

# 显示特定数据库的语录
fortune computers

# 显示所有数据库中的短语录
fortune -s

# 使用正则表达式搜索
fortune -m "linux"
```

## 工具

- **strfile**：从文本文件创建 fortune 数据库索引文件（.dat）
- **unstr**：从 .dat 文件提取原始文本

---
维护者：OpenHarmony Compiler Team
