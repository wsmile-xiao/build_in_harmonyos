# harfbuzz 14.2.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-04-25
- 编译器: clang (LLVM)
- 状态: partial

## 编译步骤
标准 autotools 流程：configure → make → make install。
需要先编译不带 harfbuzz 的 freetype（循环依赖处理）。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | harfbuzz 与 freetype 循环依赖 | 两者互相依赖 | 先编译 freetype（不带 harfbuzz），再编译 harfbuzz，最后重编译 freetype |

## 依赖版本
- freetype（不带 harfbuzz 支持的版本）

## 验证结果
编译成功，打包大小 7.7MB。无补丁应用。

## 注意事项
- harfbuzz 依赖 freetype 形成循环，需要特殊的编译顺序
- meson 构建支持较好，可考虑使用
