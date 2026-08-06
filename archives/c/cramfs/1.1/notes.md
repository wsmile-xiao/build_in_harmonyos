# cramfs 1.1 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-04-24
- 编译器: clang
- 状态: success

## 编译步骤
1. 下载源码并解压（三目录法：orig + work）
2. 应用 3 个补丁到 work 目录
3. 执行 `make CC=clang CFLAGS="-fPIC -O2 -W -Wall -I." LDLIBS="-lz" -j1`
4. 手动安装 mkcramfs 和 cramfsck 到 PREFIX/bin

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GNUmakefile 硬编码 gcc | 上游仅支持 gcc | 补丁 0001: 改为 clang |
| 2 | configure 脚本不适配 | 平台检测问题 | 补丁 0002: 构建配置适配 |
| 3 | mkcramfs.c 编译问题 | 平台兼容性 | 补丁 0003: 源码修复 |

## 源码修改
| 文件 | 修改内容 | 是否已生成补丁 |
|------|----------|----------------|
| GNUmakefile | 编译规则适配 | ✅ 0001-GNUmakefile.patch |
| configure | 构建配置适配 | ✅ 0002-configure.patch |
| mkcramfs.c | 源码修复 | ✅ 0003-mkcramfs.c.patch |

## 依赖版本
- zlib（系统自带）
- clang

## 验证结果
- `mkcramfs` → usage message ✅
- `cramfsck` → available ✅

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| cramfs-1.1-ohos-aarch64.tar.gz | 159KB | 主包 |
| cramfs-1.1-ohos-aarch64-debug.tar.gz | 92KB | Debug 包 |
---

**编译结束**: 2026-08-06 04:59
**最终状态**: built
