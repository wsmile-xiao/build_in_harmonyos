# cloc 2.08 — OpenHarmony 编译记录

## 基本信息
- 软件: cloc (Count Lines of Code)
- 版本: 2.08
- 描述: Statistics utility to count lines of code
- 构建系统: Perl (无传统编译)
- 目标: ohos-aarch64
- 许可证: GPL-2.0-or-later
- 源码: https://github.com/AlDanial/cloc/archive/refs/tags/v2.08.tar.gz

## 编译指导

cloc 是纯 Perl 脚本程序，无需传统编译流程：

```bash
# 1. 下载源码
wget https://github.com/AlDanial/cloc/archive/refs/tags/v2.08.tar.gz

# 2. 解压
tar xzf v2.08.tar.gz

# 3. 生成 man page（鸿蒙 date 命令不支持 --date=@timestamp）
cd cloc-2.08
pod2man --utf8 --center="User Commands" --name="cloc" --section="1" cloc.1.pod > cloc.1

# 4. 安装
mkdir -p $HOME/usr/local/bin $HOME/usr/local/share/man/man1
cp cloc $HOME/usr/local/bin/
cp cloc.1 $HOME/usr/local/share/man/man1/
chmod +x $HOME/usr/local/bin/cloc
```

### Perl 模块依赖
需要安装以下 Perl 模块（已包含在预编译包中）：
- Regexp::Common
- Parallel::ForkManager
- Algorithm::Diff
- Digest::MD5 (系统自带)
- File::Temp (系统自带)
- Getopt::Long (系统自带)

## 补丁清单
无补丁。Perl 脚本可直接运行。

## 已知限制

1. **鸿蒙 date 命令限制**: 不支持 `--date=@timestamp` 语法，需手动生成 man page
2. **PERL5LIB 环境变量**: 需设置 `PERL5LIB=$HOME/usr/local/lib/perl5` 才能正确加载依赖模块

## 功能验证

```bash
# 设置环境变量
export PERL5LIB=$HOME/usr/local/lib/perl5

# 版本验证
$ cloc --version
2.08

# 代码统计
$ cloc /path/to/project --quiet
github.com/AlDanial/cloc v 2.08  T=0.17 s
Language                     files          blank        comment           code
Perl                             4            910           1498          16567
SUM:                             8            951           1573          16696
```
