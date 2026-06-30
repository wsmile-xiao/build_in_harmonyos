# diff-so-fancy

## 简介

diff-so-fancy 是一个 Git diff 输出格式化工具，旨在让 diff 输出更易读，人类友好而非机器友好。

## OHOS 适配

### 适配要点

- **无编译过程**：diff-so-fancy 是纯 Perl 脚本，直接安装即可使用
- **Perl 版本**：需要 Perl 5.14 或更高版本（OpenHarmony 系统自带 Perl 5.42.0）
- **目录结构**：lib/DiffHighlight.pm 必须在 diff-so-fancy 脚本所在目录的 lib/ 下
- **tput 命令缺失**：系统可能缺少 tput 命令，会产生警告但不影响功能

### 已知问题

- `--version` 参数可能导致脚本等待输入（因为设计为管道过滤器）
- tput 缺失会产生终端宽度警告，但不影响格式化功能

### 与 Linux 的差异

无差异。Perl 脚本跨平台兼容。

## 排除与替代

无排除项。

## 依赖

### 编译依赖

无（解释型语言）

### 运行依赖

- Perl >= 5.14
- Git（可选，用于 pager 配置）
- diff 命令（可选，用于管道输入）

## 功能验证

```bash
# 基本功能测试
echo "line 1" > test_a.txt
echo "line 2" >> test_a.txt
echo "line 1" > test_b.txt
echo "line 2 modified" >> test_b.txt

diff -u test_a.txt test_b.txt | diff-so-fancy

# Git 集成测试
git config --global core.pager "diff-so-fancy | less --tabs=4 -RF"
git diff
```

## 使用说明

### Git 集成

```bash
# 设置 Git pager
git config --global core.pager "diff-so-fancy | less --tabs=4 -RF"
git config --global interactive.diffFilter "diff-so-fancy --patch"

# 可选配置
git config --bool --global diff-so-fancy.markEmptyLines true
git config --bool --global diff-so-fancy.changeHunkIndicators true
git config --bool --global diff-so-fancy.stripLeadingSymbols true
git config --bool --global diff-so-fancy.useUnicodeRuler true
```

### 独立使用

```bash
# diff 输出格式化
diff -u file_a.txt file_b.txt | diff-so-fancy

# 递归目录比较
diff --recursive -u /path/folder_a /path/folder_b | diff-so-fancy
```

## 参考

- 官方仓库：https://github.com/so-fancy/diff-so-fancy
- 发布页面：https://github.com/so-fancy/diff-so-fancy/releases