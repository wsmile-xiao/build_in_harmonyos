# perl-net-rblclient 0.5-r8 适配笔记

## 编译环境
- 构建系统: autotools (perl Makefile.PL + make)
- 编译日期: 2026-06-26（初始编译），2026-06-29（补丁修复+功能测试）
- 编译器: clang 21.1.5 (Perl 5.42.0 系统自带)
- 状态: built

## 编译步骤

```bash
# 1. 初始化构建
python3 $SKILL_ROOT/scripts/ohc-run.py init-build perl-net-rblclient 0.5-r8

# 2. 编译（纯 Perl 模块，无需 configure）
source .build-context-perl-net-rblclient-0.5-r8
cd $BUILD_SRC_DIR
perl Makefile.PL INSTALL_BASE=/
make
make install DESTDIR=$TEST_PREFIX

# 3. 测试
make check  # 无标准测试套件，通过 test_package 验证

# 4. Conan 配方生成与验证
python3 $SKILL_ROOT/scripts/ohc-run.py conan-init perl-net-rblclient 0.5-r8
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify perl-net-rblclient 0.5-r8

# 5. 功能测试（17 项，全部通过）
# 详见 reports/test-report.md

# 6. 收尾
python3 $SKILL_ROOT/scripts/ohc-run.py finish perl-net-rblclient 0.5-r8 built
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | spamalyze 脚本无法编译 | 原始源码第 108 行 `foreach my $registry qw(...)` 缺少括号（死代码中的语法错误） | 创建补丁 `0001-fix-spamalyze-syntax-error.patch`，移除 `return "x";` 之后的 5 行死代码 |
| 2 | conan-verify L2 smoke test 失败 | L2 测试通过 `--version`/`--help` 验证二进制，但 spamalyze 是 Perl 脚本，POD 声明 "No options" | 确认为误报，不影响功能可用性。17 项功能测试全部通过 |
| 3 | /tmp 只读导致测试失败 | 鸿蒙平台 E002：/tmp 文件系统只读 | 使用 $HOME/tmp 替代 |
| 4 | PERL5LIB 设置覆盖现有路径 | conan 包的 lib 路径需追加到 PERL5LIB，而非替换 | 使用 `export PERL5LIB="$PERL5LIB:<conan_lib_path>"` 追加 |

## 源码修改

### 补丁: 0001-fix-spamalyze-syntax-error.patch

**文件**: spamalyze
**修改内容**: 移除 `get_netblock` 函数中 `return "x";` 之后的死代码（5 行）

**修改前** (第 107-112 行):
```perl
    return "x";
    foreach my $registry qw( arin apnic ripe ){
        my $res = `whois $addr\@whois.arin.net`;
        return $1 if $res =~ /Netblock: (.+)/;
    }
    return "UNKNOWN";
```

**修改后** (第 107 行):
```perl
    return "x";
```

**原因**: `return "x";` 之后的代码不可达（已被 hash 查找替换的旧 whois 实现），且包含语法错误（`foreach ... qw()` 缺少括号），导致整个 spamalyze 脚本无法编译。

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| Perl | 5.42.0 | 系统自带 (/data/service/hnp/perl.org/perl_5.42.0) |
| IO::Socket | 1.55 | Perl 核心模块 |
| Time::HiRes | 1.9778 | Perl 核心模块 |
| Net::DNS | 1.55 | 用户本地安装 (/storage/Users/currentUser/usr/local/lib) |

## 验证结果

```bash
# 模块加载测试
$ perl -e "use Net::RBLClient; print $Net::RBLClient::VERSION;"
0.4

# spamalyze 语法检查（补丁后）
$ perl -c spamalyze
spamalyze syntax OK

# spamalyze 执行测试
$ echo "" | spamalyze
A                                     0

# DNS 查询测试
$ perl -e "use Net::RBLClient; my \$rbl = Net::RBLClient->new(server => '8.8.8.8'); \$rbl->lookup('127.0.0.2'); print scalar(\$rbl->listed_hash());"
2  # 127.0.0.2 被 2 个 RBL 列入

# Conan 配方验证
$ conan create . --version=0.5-r8
# ✅ 构建成功，test_package 测试通过
```

## 注意事项

1. **纯 Perl 模块**: 无 XS/C 代码，不受 SELinux HMDFS 限制影响（对比 perl-dbd-pg 的 XS 模块限制）
2. **L2 误报**: conan-verify 的 L2 smoke test 对 Perl 脚本是误报，不影响上库
3. **Net::DNS 依赖**: 系统需安装 Net::DNS 模块（非 Perl 核心模块），已预装在用户本地路径
4. **PERL5LIB 配置**: 使用 conan 包时需追加（非替换）PERL5LIB 路径
5. **spamalyze 无选项**: 脚本不支持 --version/--help，通过 STDIN 或文件参数输入

---

**编译结束**: 2026-06-29 17:25
**最终状态**: built
**功能测试**: 17/17 PASS
