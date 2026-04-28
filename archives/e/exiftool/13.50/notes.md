# exiftool 13.50 适配笔记

## 编译环境
- 构建系统: custom (Perl MakeMaker)
- 编译日期: 2026-04-22
- 编译器: N/A (Perl 模块)
- 状态: published

## 编译步骤
```bash
perl Makefile.PL PREFIX=$HOME/usr/local
make
make test
make install DESTDIR=$TEST_PREFIX
# 复制模块到 bin/lib 解决路径问题
cp -r lib/site_perl/*/Image bin/lib/
cp -r lib/site_perl/*/File bin/lib/
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 下载 URL 404 | exiftool.org 主站链接失效 | 使用 SourceForge 镜像 |
| 2 | Can't locate Image/ExifTool.pm | Perl @INC 不含安装路径 | 复制模块到 bin/lib/（exiftool 自动添加到 @INC）|

## 源码修改
无补丁。

## 依赖版本
- Perl >= 5.42.0（已预装）

## 验证结果
- make test: 113 文件, 600 断言, 全部 PASS
- exiftool -ver = 13.50 ✅

## 交付物
- bin/exiftool (Perl 脚本)
- bin/lib/Image/ExifTool/ (200+ Perl 模块)
- bin/lib/File/RandomAccess.pm

## 注意事项
- 需设置 PERL5LIB 或使用 bin/lib 结构
- 预编译包较大 (38MB)，包含所有 Perl 模块
