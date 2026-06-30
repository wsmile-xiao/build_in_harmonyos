# perl-locale-codes

## 简介
Locale-Codes 是一个纯 Perl 模块，提供标准化的地区代码查询功能，包括：
- 国家代码 (ISO 3166)
- 语言代码 (ISO 639)
- 货币代码 (ISO 4217)
- 脚本代码 (ISO 15924)

## OHOS 适配
- **模块类型**: 纯 Perl，无 XS 代码，无 SELinux HMDFS 限制
- **安装位置**: `~/usr/local/lib/site_perl/5.42.0/Locale/`
- **即用性**: ✅ 安装后立即可用（需配置 PERL5LIB）
- **测试状态**: ✅ 1230 单元测试 + 33 功能测试全部通过

## 版本历史
| 版本 | 状态 | 测试 | 日期 |
|------|------|------|------|
| 3.85-r0 | published | PASS (1230+33) | 2026-06-15 |

## 安装方法

### 方法一：使用 cmd-pkgs 安装脚本（推荐）
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-locale-codes 3.85-r0
```

### 方法二：手动安装
```bash
# 下载预编译包
wget https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/perl-locale-codes-3.85-r0-ohos-aarch64.tar.gz

# 解压到用户目录
tar -xzf perl-locale-codes-3.85-r0-ohos-aarch64.tar.gz -C ~/usr/local/
```

### ⚠️ 安装后配置（必须）

Perl 模块安装到 `~/usr/local/lib/site_perl/5.42.0/`，但 Perl 默认搜索路径不包括此目录。**需要配置 PERL5LIB 环境变量**：

#### 临时配置（当前会话）
```bash
export PERL5LIB=~/usr/local/lib/site_perl/5.42.0

# 验证安装
perl -e 'use Locale::Codes; print "Version: $Locale::Codes::VERSION\n";'
# 输出: Version: 3.85
```

#### 持久配置（写入配置文件）
```bash
# 添加到 ~/.bashrc 或 ~/.profile
echo 'export PERL5LIB=~/usr/local/lib/site_perl/5.42.0' >> ~/.bashrc
source ~/.bashrc
```

#### 多版本 Perl 支持
如果安装了多个版本的 Perl 模块，可以设置多个路径：
```bash
export PERL5LIB=~/usr/local/lib/site_perl/5.42.0:~/usr/local/lib/site_perl/5.42.0/aarch64-linux
```

## 使用示例

### 国家代码查询
```perl
use Locale::Country;

# 代码 → 名称
print code2country('us'), "\n";   # 输出: United States of America
print code2country('cn'), "\n";   # 输出: China
print code2country('jp'), "\n";   # 输出: Japan

# 名称 → 代码
print country2code('China'), "\n";    # 输出: cn
print country2code('日本'), "\n";      # 输出: jp (支持中文)

# 获取所有国家代码
my @codes = all_country_codes();  # 249 个国家代码
```

### 语言代码查询
```perl
use Locale::Language;

print code2language('zh'), "\n";      # 输出: Chinese
print code2language('en'), "\n";      # 输出: English
print language2code('Chinese'), "\n"; # 输出: zh

my @codes = all_language_codes();     # 185 个语言代码
```

### 货币代码查询
```perl
use Locale::Currency;

print code2currency('usd'), "\n";     # 输出: US Dollar
print code2currency('eur'), "\n";     # 输出: Euro
print currency2code('US Dollar'), "\n"; # 输出: USD

my @codes = all_currency_codes();     # 177 个货币代码
```

### 脚本代码查询
```perl
use Locale::Script;

print code2script('Latn'), "\n";      # 输出: Latin
print code2script('Arab'), "\n";      # 输出: Arabic
print script2code('Latin'), "\n";     # 输出: Latn

my @codes = all_script_codes();       # 223 个脚本代码
```

## 验证安装
安装后执行以下命令验证：
```bash
# 设置环境变量
export PERL5LIB=~/usr/local/lib/site_perl/5.42.0

# 测试模块加载
perl -e 'use Locale::Codes; print "OK: Version $Locale::Codes::VERSION\n";'
perl -e 'use Locale::Country; print code2country("cn"), "\n";'
perl -e 'use Locale::Language; print code2language("zh"), "\n";'
perl -e 'use Locale::Currency; print code2currency("usd"), "\n";'
perl -e 'use Locale::Script; print code2script("Latn"), "\n";'
```

预期输出：
```
OK: Version 3.85
China
Chinese
US Dollar
Latin
```

## 依赖
- **运行依赖**: Perl >= 5.42.0
- **测试依赖**: Test::Inter >= 1.09（可选，仅用于测试）

## 许可证
Perl Artistic License

## 参考
- CPAN: https://metacpan.org/release/Locale-Codes
- ISO 3166 (国家代码)
- ISO 639 (语言代码)
- ISO 4217 (货币代码)
- ISO 15924 (脚本代码)

---
维护者: OpenHarmonyPCDeveloper
最后更新: 2026-06-15