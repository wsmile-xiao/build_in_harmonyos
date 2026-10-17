# farbfeld 4 适配笔记

## 编译环境
- 构建系统: makefile (suckless style)
- 编译日期: 2026-08-06
- 编译器: clang 15.0.4
- 状态: built (conan recipe verified)

## 源码
- 官方地址: https://dl.suckless.org/farbfeld/farbfeld-4.tar.gz
- SHA256: c7df5921edd121ca5d5b1cf6fb01e430aff9b31242262e4f690d3af72ccbe72a

## 编译步骤
1. 使用 conan install 安装依赖 (libpng/1.6.58, libjpeg/10)
2. make 编译，通过命令行覆盖 CC/CFLAGS/CPPFLAGS/LDFLAGS/PNG-LDLIBS/JPG-LDLIBS
3. 复制二进制文件到 package bin 目录 (conan.tools.files.copy)

## 依赖
| 依赖 | 版本 | 用途 |
|------|------|------|
| libpng | 1.6.58 | ff2png, png2ff (PNG 转换) |
| libjpeg | 10 | ff2jpg, jpg2ff (JPEG 转换) |

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.mk 使用硬编码 CC=cc | suckless 默认为本地编译 | conanfile.py 通过 make 命令行覆盖 CC |
| 2 | 缺少 libpng/libjpeg | 系统未安装这些库 | 通过 conan requires 声明依赖 |

## 功能验证
- ff2ppm: farbfeld → PPM ✓
- ff2pam: farbfeld → PAM ✓
- ff2png: farbfeld → PNG ✓
- ff2jpg: farbfeld → JPEG ✓

## Conan 配方
- package_type: application (命令行工具)
- 通过 make 命令行变量覆盖实现交叉编译
- test_package: Python 脚本测试所有转换工具
---

**编译结束**: 2026-08-06 10:26
**最终状态**: built
