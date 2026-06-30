# diff-so-fancy 1.4.10 适配笔记

## 编译环境
- 构建系统: custom（Perl 脚本，无需编译）
- 编译日期: 2026-05-19
- 编译器: N/A（解释型语言）
- Perl 版本: 5.42.0
- 状态: built

## 编译步骤

diff-so-fancy 是一个纯 Perl 脚本项目，无需传统编译。安装步骤如下：

1. 创建目标目录结构：
   ```bash
   mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin/lib
   ```

2. 复制文件到安装位置：
   ```bash
   cp diff-so-fancy $TEST_PREFIX/$DEFAULT_PREFIX/bin/
   cp lib/DiffHighlight.pm $TEST_PREFIX/$DEFAULT_PREFIX/bin/lib/
   chmod +x $TEST_PREFIX/$DEFAULT_PREFIX/bin/diff-so-fancy
   ```

3. 目录结构：
   ```
   $PREFIX/
   └── bin/
       ├── diff-so-fancy (主脚本)
       └── lib/
           └── DiffHighlight.pm (依赖模块)
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | --version 命令超时 | diff-so-fancy 设计为管道过滤器，不适用于直接运行 | 使用管道方式测试：`diff -u a.txt b.txt \| diff-so-fancy` |
| 2 | tput 命令缺失警告 | 系统未安装 ncurses/tput | 功能不受影响，仅显示宽度计算警告 |
| 3 | 测试工具 bats 缺失 | 系统无 bats 测试框架 | 跳过单元测试，使用功能测试验证 |

## 源码修改

无需修改源码。原版 diff-so-fancy 可直接在 OpenHarmony 上运行。

## 依赖版本

| 软件 | 版本 | 说明 |
|------|------|------|
| Perl | 5.42.0 | 系统自带，满足 >= 5.14 要求 |
| diff | 系统内置 | 用于生成 diff 输出 |
| Git | 2.x（可选） | 作为 pager 使用时需要 |

## 验证结果

功能测试通过：

```bash
# 创建测试文件
echo "line 1" > test_a.txt
echo "line 2" >> test_a.txt
echo "line 1" > test_b.txt
echo "line 2 modified" >> test_b.txt

# 运行 diff-so-fancy
diff -u test_a.txt test_b.txt | diff-so-fancy
```

输出结果（带颜色格式化）：
```
────────────────────────────────────────
renamed: test_a.txt to test_b.txt
────────────────────────────────────────
@ test_b.txt:1 @
line 1
line 2
line 2 modified
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| diff-so-fancy-1.4.10-ohos-aarch64.tar.gz | ~50KB | 预编译包（Perl 脚本 + 依赖模块） |

## 使用说明

### 安装

通过 cmd-pkgs 公共安装脚本安装：
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- diff-so-fancy 1.4.10
```

### 配置 Git 集成

```bash
# 设置 Git 使用 diff-so-fancy
git config --global core.pager "diff-so-fancy | less --tabs=4 -RF"
git config --global interactive.diffFilter "diff-so-fancy --patch"

# 可选：配置显示选项
git config --bool --global diff-so-fancy.markEmptyLines true
git config --bool --global diff-so-fancy.changeHunkIndicators true
git config --bool --global diff-so-fancy.stripLeadingSymbols true
```

### 独立使用

```bash
# 作为 diff 过滤器
diff -u file_a.txt file_b.txt | diff-so-fancy

# 递归比较目录
diff --recursive -u /path/folder_a /path/folder_b | diff-so-fancy
```

## 注意事项

1. **无编译产物**：diff-so-fancy 是纯 Perl 脚本，无需编译，直接安装即可使用
2. **lib 目录位置**：lib/DiffHighlight.pm 必须在 diff-so-fancy 脚本所在目录的 lib/ 下
3. **Perl 版本要求**：需要 Perl 5.14 或更高版本（当前系统 5.42.0 满足）
4. **tput 警告**：系统缺少 tput 命令会产生警告，但不影响功能（仅影响终端宽度检测）
5. **测试跳过**：缺少 bats 测试框架，使用功能测试替代单元测试
---

**编译结束**: 2026-05-19 23:18
**最终状态**: built
