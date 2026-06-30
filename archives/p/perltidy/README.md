# perltidy

**描述**: Perl 代码格式化和美化工具

**许可证**: GPL-2.0-or-later

**主页**: https://perltidy.sourceforge.net/

**源码仓库**: https://github.com/perltidy/perltidy

## 编译版本

| 版本 | 状态 | 日期 | 备注 |
|------|------|------|------|
| 20260204 | published | 2026-05-27 | 纯Perl软件，Makefile.PL构建 |

## 构建系统

custom-perl (Makefile.PL + ExtUtils::MakeMaker)

## 运行依赖

- Perl >= 5.8.1 (系统预装 Perl v5.42.0)
- 需设置 PERL5LIB 环境变量以加载模块

## 注意事项

- perltidy 是纯 Perl 软件，无 ELF 二进制文件
- Perl 模块安装在 $DEFAULT_PREFIX/lib/site_perl/ 下，不在系统 Perl 的 @INC 中
- 运行时需设置 `PERL5LIB="$DEFAULT_PREFIX/lib/site_perl/5.42.0"`