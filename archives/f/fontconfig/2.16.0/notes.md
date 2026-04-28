# fontconfig 2.16.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-04-25
- 编译器: clang
- 状态: partial

## 编译步骤
1. 下载源码 `https://www.freedesktop.org/software/fontconfig/release/fontconfig-2.16.0.tar.xz`
2. `./configure --prefix=$DEFAULT_PREFIX`
3. `make -j$(nproc)`
4. `make install`
5. 设置 FONTCONFIG_PATH 环境变量

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 缺少 freetype 依赖 | 编译顺序问题 | 先编译安装 freetype |
| 2 | 缺少 expat 依赖 | 编译顺序问题 | 先编译安装 expat |
| 3 | 配置文件路径未设置 | OHOS 默认路径不同 | 设置 FONTCONFIG_PATH 环境变量 |

## 依赖版本
- freetype（必须）
- expat（必须）

## 注意事项
- 编译 PROGRESS.md 为模板状态，具体步骤待补充
- 需要 FONTCONFIG_PATH 环境变量
