# hebcal 4.31 编译笔记

## 基本信息
- 软件: hebcal (犹太日历程序)
- 版本: 4.31 (最后的C语言稳定版本)
- 语言: C
- 构建系统: autotools

## 源码信息
- URL: https://api.github.com/repos/hebcal/hebcal/tarball/v4.31
- SHA256: (待计算)
- 格式: tar.gz

## 编译过程

### 问题1: HMDFS文件系统权限问题
configure脚本在HMDFS文件系统上创建临时文件时遇到权限错误:
```
./config.status[744]: can't create ./confXXXX/subs1.awk: Permission denied
```

### 解决方案
1. 将源码复制到 `$TMPDIR/hebcal-build` 进行构建
2. 从automake share目录复制辅助文件:
   - config.guess
   - config.sub
   - compile
   - missing
   - depcomp
   - install-sh
3. 手动创建config.h
4. 使用po2gperf.pl生成翻译文件(strings_*.c)
5. 手动创建Makefile完成编译

### 编译命令
```bash
cd $TMPDIR/hebcal-build
perl po2gperf.pl po/*.po
make
```

## 编译结果
- 二进制: hebcal (1.2MB)
- 功能验证: hebcal --version => "Hebcal version 4.31"
- 功能验证: hebcal => 正确输出希伯来日历节日

## 知识沉淀
- E07?: HMDFS文件系统上configure脚本临时文件创建失败
- 解决方案: 使用$TMPDIR进行构建，手动创建必要文件
---

**编译结束**: 2026-06-12 14:57
**最终状态**: built
