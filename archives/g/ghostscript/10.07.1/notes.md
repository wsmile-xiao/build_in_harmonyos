# ghostscript 10.07.1 适配笔记

## 编译环境
- 构建系统: autotools (自定义configure)
- 编译日期: 2026-05-26
- 编译器: clang 15.0.4/clang++
- 状态: built

## 编译步骤
1. init-build下载源码（ghostscript-10.07.1.tar.gz）
2. 修改config.guess添加HarmonyOS检测分支
3. 修改configure修复umask 077→022（HMDFS权限限制）
4. 同样修复内嵌子项目的config.guess（ijs、jpeg、lcms2mt、libpng、tiff）
5. bash ./configure --prefix=$DEFAULT_PREFIX
6. make -j1
7. make install DESTDIR=$TEST_PREFIX
8. package生成预编译包（aarch64 + aarch64-debug）
9. make install（本地安装）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess不识别HarmonyOS | GNU config.guess缺少ohos检测 | 添加HarmonyOS分支（E007） |
| 2 | configure中umask 077导致临时目录权限错误 | HMDFS文件系统umask限制 | sed修改configure中umask 077→022 |
| 3 | 内嵌子项目config.guess同理 | 各子项目自带config.guess | 同样添加HarmonyOS分支 |

## 补丁文件
- 0001-config.guess.patch: 主config.guess HarmonyOS检测
- 0002-configure.patch: umask 077→022修复
- 0003-ijs-config.guess.patch: ijs子项目config.guess
- 0004-jpeg-config.guess.patch: jpeg子项目config.guess
- 0005-lcms2mt-config.guess.patch: lcms2mt子项目config.guess
- 0006-libpng-config.guess.patch: libpng子项目config.guess
- 0007-tiff-config-config.guess.patch: tiff子项目config.guess

## 验证结果
```bash
$ gs --version
10.07.1
```

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| ghostscript-10.07.1-ohos-aarch64.tar.gz | 47MB | Release制品 |
| ghostscript-10.07.1-ohos-aarch64-debug.tar.gz | 264KB | Debug符号包 |

## 注意事项
- ghostscript内嵌大量第三方库（zlib、libpng、jpeg、tiff、freetype等），编译时无需额外安装这些依赖
- 所有修改已保存为7个patch文件，遵循不直接修改源码原则
---

**编译结束**: 2026-05-26 19:25
**最终状态**: built
