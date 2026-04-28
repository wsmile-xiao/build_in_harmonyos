# cloc

## 简介
cloc (Count Lines of Code) 是一个代码行数统计工具，使用 Perl 实现，支持多种编程语言。

## OHOS 适配
- 纯 Perl 脚本程序，无需传统编译
- 鸿蒙 date 命令不支持 `--date=@timestamp` 语法，需手动运行 pod2man 生成 man page
- 需设置 `PERL5LIB=$HOME/usr/local/lib/perl5` 环境变量

## 依赖
- Perl >= 5.10.0
- Regexp::Common, Parallel::ForkManager, Algorithm::Diff (打包在预编译包中)

## 功能验证
```bash
cloc --version  # 输出: 2.08
cloc /path/to/project --quiet
```

## 参考
- 官网: https://github.com/AlDanial/cloc
