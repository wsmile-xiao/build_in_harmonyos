# Lingua::EN::Inflect

Perl模块 - 英语单词词形变化（复数、动词变位、数字转单词等）

## 软件简介

Lingua::EN::Inflect 是一个纯Perl实现的英语词形变化模块，用于处理英语单词的形态变化。该模块广泛应用于自然语言处理、文本生成、数据展示等场景。

## 核心功能

### 1. 名词复数化
```perl
use Lingua::EN::Inflect qw(PL PL_N);
print PL('cat');      # 输出: cats
print PL_N('person'); # 输出: people
print PL('mouse');    # 输出: mice
```

### 2. 动词变位
```perl
use Lingua::EN::Inflect qw(PL_V PL_ADJ);
print PL_V('runs');    # 输出: run
print PL_ADJ('better'); # 输出: best
```

### 3. 数字转单词
```perl
use Lingua::EN::Inflect qw(NUMWORDS);
print NUMWORDS(123);     # 输出: one hundred and twenty-three
print NUMWORDS(1_000_000); # 输出: one million
```

### 4. 单词列表处理
```perl
use Lingua::EN::Inflect qw(WORDLIST);
print WORDLIST(['cat', 'dog', 'bird']); # 输出: cat, dog and bird
```

### 5. 古典模式
```perl
use Lingua::EN::Inflect qw(classical NO);
classical;  # 启用古典模式
print PL('formula'); # 输出: formulae（古典）
NO('classical');     # 关闭古典模式
print PL('formula'); # 输出: formulas（现代）
```

## 版本信息

- **版本号**: 1.905-r1
- **发布日期**: 2026-06-12
- **CPAN作者**: Damian Conway (DCONWAY)
- **官方主页**: https://metacpan.org/pod/Lingua::EN::Inflect

## OpenHarmony适配

### 编译状态
- ✅ 已编译通过
- ✅ 测试100%通过（2147/2147测试用例）
- ✅ 已发布预编译包

### 模块特性
- **模块类型**: 纯Perl（Pure Perl）
- **XS依赖**: 无
- **平台限制**: 无（不受SELinux HMDFS限制）

### 安装方式
```bash
# 使用预编译包安装（推荐）
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-lingua-en-inflect 1.905-r1

# 或使用Perl安装（需已安装Perl）
perl Makefile.PL PREFIX=/storage/Users/currentUser/usr/local
make install
```

### 使用示例
```perl
# 加载模块
use Lingua::EN::Inflect qw(PL NUMWORDS WORDLIST);

# 名词复数化
my $plural = PL('apple');  # apples

# 数字转单词
my $words = NUMWORDS(42);  # forty-two

# 单词列表
my $list = WORDLIST(['red', 'green', 'blue']);  # red, green and blue

# 获取模块版本
print $Lingua::EN::Inflect::VERSION;  # 1.905
```

## 依赖关系

### 运行时依赖
- Perl 5.42.0

### 编译时依赖
- Test::More（测试依赖）

## 编译笔记

详见 `1.905-r1/notes.md`

### 关键发现

1. **纯Perl模块编译简单**
   - 无需XS编译参数
   - 无需处理链接器问题

2. **对比XS模块（perl-dbd-pg）**
   - XS模块需要 `-nostartfiles -nodefaultlibs` 参数
   - XS模块受SELinux HMDFS限制
   - 纯Perl模块可用户目录直接加载

3. **质量门禁适配**
   - G4无二进制文件是正常情况（纯Perl模块无.so文件）

## 测试报告

- **测试文件**: 15个
- **测试用例**: 2147个
- **通过率**: 100%
- **详细报告**: `1.905-r1/reports/test-report.md`

## 许可证

Perl Artistic License / GNU GPL

## 参考链接

- [CPAN主页](https://metacpan.org/pod/Lingua::EN::Inflect)
- [源码仓库](https://github.com/DCONWAY/Lingua-EN-Inflect)
- [OpenHarmony预编译包](https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs)

---

**维护者**: OpenHarmony三方库预编译框架
**最后更新**: 2026-06-13