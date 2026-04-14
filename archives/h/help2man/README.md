# GNU help2man 1.49.3 for HarmonyOS/OpenHarmony

## 概述

GNU help2man 是一个从 `--help` 和 `--version` 输出生成 man 页面的工具。

## 软件信息

| 项目 | 信息 |
|------|------|
| 软件名称 | GNU help2man |
| 版本 | 1.49.3 |
| 官方网站 | https://www.gnu.org/software/help2man/ |
| 下载地址 | https://ftp.gnu.org/gnu/help2man/help2man-1.49.3.tar.xz |

## 特点

- **纯 Perl 脚本**：不需要编译
- **自解压安装**：help2man.PL 自动检测并嵌入正确的 perl 路径
- **无需修改 shebang**：安装脚本自动处理

## 安装步骤

```bash
# 1. 下载并解压
curl -L -o help2man-1.49.3.tar.xz https://ftp.gnu.org/gnu/help2man/help2man-1.49.3.tar.xz
tar -xf help2man-1.49.3.tar.xz
cd help2man-1.49.3

# 2. 生成并安装
perl help2man.PL --stdout > $HOME/usr/local/bin/help2man
chmod +x $HOME/usr/local/bin/help2man

# 3. 首次运行需要用户确认（鸿蒙安全机制）
help2man --version

# 4. 验证安装
help2man --version
# 输出: GNU help2man 1.49.3
```

## 使用方法

```bash
# 为程序生成 man 页面
help2man --name="program description" /path/to/program > program.1

# 示例：为 ls 生成 man 页面
help2man --name="list directory contents" $HOME/usr/local/bin/ls > ls.1

# 安装 man 页面
cp program.1 $HOME/usr/local/share/man/man1/
```

## 鸿蒙特殊说明

### 首次运行确认

鸿蒙系统对新安装的二进制文件有安全限制：
- 首次执行时会弹出确认窗口
- 需要在 30 秒内点击确认
- 确认后才能正常执行

### 自动 shebang 处理

help2man.PL 是自解压脚本，会自动检测系统中的 perl 路径并嵌入：

```bash
# 生成的脚本自动包含正确的 perl 路径
$ head -1 $HOME/usr/local/bin/help2man
#!/data/service/hnp/perl.org/perl_5.42.0/bin/perl -w
```

**不需要手动修改 shebang！**

## 依赖

- Perl 5.8+
- sed（用于管道文本处理，需要修复 fstat 问题）

## 常见问题

### Q: 执行脚本报 "operation not permitted"

**A:** 这是鸿蒙安全机制，首次执行需要用户确认。点击弹窗确认后即可正常执行。

### Q: 生成的 man 页面为空或报错

**A:** 确保目标程序支持 `--help` 和 `--version` 选项，并且 PATH 中使用的是修复后的 GNU sed。

## 版本历史

| 日期 | 版本 | 说明 |
|------|------|------|
| 2026-03-16 | 1.0 | 初始版本 |