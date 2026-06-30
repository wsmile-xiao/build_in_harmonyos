# ExtUtils::CppGuess

## 简介
ExtUtils::CppGuess attempts to guess the system's C++ compiler that is compatible with the C compiler that your Perl was built with. It provides configuration options for both ExtUtils::MakeMaker and Module::Build based Perl modules.

## OHOS 适配
- **纯 Perl 模块**: 无 XS 代码，不需要编译 C/C++ 代码到原生库
- **编译器检测**: 读取 Perl 的 $Config{cc} 和相关配置，猜测 C++ 编译器
- **测试受限**: 测试尝试编译 C++ 测试程序验证检测结果，OHOS 平台可能缺少完整的 C++ 工具链
- **安装方式**: `perl Makefile.PL && make && make install`（可跳过测试）
- **依赖**: perl 5.10+, Capture::Tiny, File::Temp, ExtUtils::ParseXS 3.35+

## 功能验证
```bash
perl -MExtUtils::CppGuess -e 'print "ExtUtils::CppGuess version: $ExtUtils::CppGuess::VERSION\n"'
```

核心功能测试：
```perl
use ExtUtils::CppGuess;
my $guess = ExtUtils::CppGuess->new;
print "CCFLAGS: ", $guess->makemaker_options->{CCFLAGS}, "\n";
```

## 排除与替代
- 测试套件可能因 C++ 编译器检测失败而跳过
- 核心模块功能（配置猜测）不依赖测试通过
- 用于需要 C++ 编译的 Perl XS 模块的构建配置

## 依赖
- **运行依赖**: Capture::Tiny, File::Temp, ExtUtils::ParseXS
- **构建依赖**: perl, ExtUtils::MakeMaker

## 参考
- CPAN: https://metacpan.org/pod/ExtUtils::CppGuess
- 源码: https://cpan.metacpan.org/authors/id/E/ET/J/ExtUtils-CppGuess-0.27.tar.gz
- GitHub: https://github.com/tsee/extutils-cppguess