# tmx 1.10.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-16
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码: https://github.com/baylej/tmx/archive/refs/tags/tmx_1.10.1.tar.gz (因SSL证书问题通过 ghfast.top 镜像手动下载)
2. 安装依赖: zlib 1.3.1 (通过 cmd-pkgs 预编译包安装)
3. configure: `cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release ..`
4. make: `make -j1` (1 warning: tmx_utils.c:112 比较常量-1与char类型)
5. make install DESTDIR=$TEST_PREFIX: 安装到 staging 目录
6. make install: 安装到 ~/usr/local
7. 预编译包制作: ohc-run.py package → tmx-1.10.1-ohos-aarch64.tar.gz (122KB)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书下载失败 | 系统SSL证书验证失败 | 使用 ghfast.top 镜像+curl -k 手动下载，然后 --no-download 模式初始化 |
| 2 | 构建系统检测错误 | init-build 将 cmake 项目误检测为 autotools | 手动修正 manifest.yaml 和 .build-context 中 BUILD_SYSTEM 为 cmake |
| 3 | cmake configure 失败 (ZLIB missing) | tmx 依赖 zlib，cmake 找不到 libz | 安装 zlib 1.3.1 预编译包，设置 PKG_CONFIG_PATH |
| 4 | G0 干净构建验证失败 | clean-verify 环境缺少 zlib | 需要在 manifest.yaml 中记录 zlib 依赖，clean-verify 会自动安装 |

## 源码修改

无补丁，无源码修改。仅有一个编译警告 (tmx_utils.c:112) 但不影响功能。

## 依赖版本

| 依赖 | 版本 | 安装方式 |
|------|------|----------|
| zlib | 1.3.1 | cmd-pkgs 预编译包 |
| libxml2 | 2.15.3 | 已预装 |

## 验证结果

```bash
# Staging 验证通过
# 本地安装验证:
ls ~/usr/local/lib/libtmx.a    # 验证库文件存在
ls ~/usr/local/include/tmx.h    # 验证头文件存在
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| tmx-1.10.1-ohos-aarch64.tar.gz | 122KB | 预编译包 |

## 注意事项

- tmx 是纯 C 静态库 (libtmx.a)，无可执行二进制
- 依赖 zlib 和 libxml2（通过 cmake find_package 查找）
- cmake 在 HarmonyOS 平台会输出 "System is unknown" 警告，但不影响编译
---

**编译结束**: 2026-06-16 12:39
**最终状态**: published
