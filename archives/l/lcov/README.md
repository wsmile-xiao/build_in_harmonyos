# lcov

## 描述

LCOV (Linux Test Project Coverage) 是一个用于 GCC 覆盖率测试工具 gcov 的图形化前端工具。它收集 gcov 数据并创建 HTML 格式的覆盖率报告。

## 功能特性

- HTML 输出：覆盖率以条形图和颜色标记显示，便于快速诊断覆盖率问题
- 支持大型项目：提供分层目录结构视图
- 支持多种语言：C/C++, Perl, Python 等
- 支持差分覆盖率、日期分组和所有者分组
- 支持多种覆盖率工具：gcov, llvm-cov, Coverage.py, Cobertura, Devel::Cover, Jacaco 等

## 安装

### 从预编译包安装

下载 `lcov-{version}-ohos-aarch64.tar.gz`，解压到目标位置：

```bash
tar -xzf lcov-2.4-ohos-aarch64.tar.gz -C $HOME/usr/local --strip-components=0
```

### 运行时依赖

lcov 需要以下 Perl 模块：
- perl >= 5.10
- Capture::Tiny
- JSON
- Try::Tiny
- Date::Parse
- Time::Piece (Perl 核心模块，替代 DateTime)

**安装 Perl 模块（如果缺失）**：
```bash
# 手动安装示例
cpan Capture::Tiny
cpan JSON
cpan Try::Tiny
cpan TimeDate  # 包含 Date::Parse
```

**注意**: DateTime 模块已通过补丁替换为 Time::Piece（Perl 核心模块），无需额外安装。

## 使用方法

基本用法：
```bash
# 捕获覆盖率数据
lcov --capture --directory . --output-file coverage.info

# 生成 HTML 报告
genhtml coverage.info --output-directory out
```

详细用法请参考：
- lcov man page (`man lcov`)
- [官方文档](https://github.com/linux-test-project/lcov)

## 已编译版本

| 版本 | 状态 | 日期 | 备注 |
|------|------|------|------|
| 2.4 | success | 2026-05-20 | Perl 模块依赖已解决，DateTime 替换为 Time::Piece |

## 补丁说明

lcov 2.4 使用补丁解决 DateTime 模块依赖问题：
- `0001-replace-DateTime-with-Time-Piece-lcovutil.patch` - lcovutil.pm 修改
- `0002-replace-DateTime-with-Time-Piece-genhtml.patch` - genhtml 修改

## 许可证

GPL-2.0

## 官方网站

https://github.com/linux-test-project/lcov