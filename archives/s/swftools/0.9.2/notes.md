# swftools 0.9.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-08
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化编译环境: `ohc-run.py init-build swftools 0.9.2 --url=...`
2. 修改 configure 脚本，使用 TMPDIR 创建临时目录
3. 修改 config.status 使用 TMPDIR 和绝对路径命令
4. 修复源码中的重复符号问题：
   - voidclass 在 registry.h 中重复定义
   - filename/line/column/cleanUp 在 swfc-feedback.h 中重复定义
   - noBlur/noDropshadow/noBevel/noGradientGlow/noFilters 在 swfc-history.h 中重复定义
5. 编译: `make -j1`
6. 安装: 创建 staging 目录并复制文件

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status 无法创建临时文件 | mktemp 创建的目录权限太严格（700），用户 ID 不匹配 | 修改 config.status 使用 TMPDIR 和预创建的临时目录 |
| 2 | 重复符号 voidclass | registry.h 中既有定义又有 extern 声明 | 将 registry.h 第 156 行改为 extern 声明 |
| 3 | 重复符号 filename/line/column/cleanUp | swfc-feedback.h 头文件中直接定义全局变量 | 改为 extern 声明，在 swfc.c 中定义 |
| 4 | 重复符号 noBlur 等 | swfc-history.h 头文件中直接定义全局变量 | 改为 extern 声明，在 swfc.c 中定义 |

## 源码修改

- lib/as3/registry.h: 将 voidclass 定义改为 extern 声明
- src/swfc-feedback.h: 将 filename/line/column/cleanUp 定义改为 extern 声明
- src/swfc-history.h: 将 noBlur/noDropshadow/noBevel/noGradientGlow/noFilters 定义改为 extern 声明
- src/swfc.c: 添加全局变量的实际定义

## 依赖版本

- zlib (系统自带)
- clang 15.0.4

## 验证结果

编译成功，生成了以下工具：
- wav2swf, png2swf, swfcombine, swfstrings, swfextract, swfdump
- swfc, swfbbox, font2swf, swfrender, as3compile, swfbytes, ttftool

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| swfcombine | 160KB | SWF 组合工具 |
| swfdump | 394KB | SWF 分析工具 |
| swfc | 1.1MB | SWF 编译器 |
| 其他工具 | 见 staging 目录 | 共 13 个可执行文件 |

## 注意事项

- 缺少 jpeglib、giflib、freetype 等依赖，pdf2swf、jpeg2swf、gif2swf 工具被禁用
- 源码有多处全局变量重复定义的 bug，需要修复
---

**编译结束**: 2026-06-08 18:54
**最终状态**: built
