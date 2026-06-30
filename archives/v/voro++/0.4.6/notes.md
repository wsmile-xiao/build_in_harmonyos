# voro++ 0.4.6 适配笔记

## 编译环境

- **构建系统**: makefile（自定义 Makefile + config.mk）
- **编译日期**: 2026-06-03
- **编译器**: clang 15.0.4 / clang++ 15.0.4
- **目标架构**: aarch64 (OpenHarmony)
- **状态**: published

## 编译步骤

voro++ 使用自定义 Makefile 构建系统，无 autotools 也无 cmake。编译步骤如下：

1. **源码下载**: 从 Debian snapshot 镜像获取 voro++_0.4.6+dfsg1.orig.tar.gz（Savannah/GitHub 官方源均 404 或 SSL 问题）
2. **初始化**: `python3 ohc-run.py init-build voro++ 0.4.6`
3. **修改 config.mk**: 设置 CXX=clang++、CFLAGS="-Wall -ansi -pedantic -O2 -fPIC"
4. **修改 Makefile**: 添加 DESTDIR= 支持，将所有 $(PREFIX) 替换为 $(DESTDIR)$(PREFIX)
5. **创建 configure wrapper**: 因 G0 clean-verify 硬编码执行 `./configure`，创建 wrapper 脚本解析 --prefix 参数并修改 config.mk
6. **编译**: `make -j1`（成功，1个 unused variable 警告）
7. **安装**: `make install DESTDIR=$TEST_PREFIX`（staging 安装）
8. **验证**: `voro++ --version` → 输出正常
9. **打包**: `python3 ohc-run.py package voro++ 0.4.6`
10. **收尾**: `python3 ohc-run.py finish voro++ 0.4.6 published`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 源码下载 404/SSL 错误 | Savannah 官方站不可用，GitHub 镜像 SSL 证书问题 | 使用 Debian snapshot 镜像下载 |
| 2 | Makefile 不支持 DESTDIR | 上游 Makefile 中 install 目标直接使用 $(PREFIX) | 修改 Makefile，将 $(PREFIX) 替换为 $(DESTDIR)$(PREFIX) |
| 3 | G0 clean-verify 硬编码执行 ./configure | ohc-run.py 的 clean_verify.py 对所有构建系统均执行 `./configure` | 创建 configure wrapper 脚本，解析参数修改 config.mk，生成 config.status |
| 4 | G4 门禁找不到 build_system 字段 | verify_build.py 检查扁平 `build_system:` 而非嵌套 `build: system:` | 在 manifest.yaml 添加扁平格式 `build_system: makefile` |
| 5 | G0 configure 执行报错 "no closing quote" | manifest.yaml 中 configure_options 为 YAML 列表格式，被 shell 误解析 | 简化 configure_options 为空字符串 "" |
| 6 | 二进制版本号显示 0.4.5 | 上游 cmd_line.cc 中版本号字符串未更新至 0.4.6 | 已知上游问题，NEWS 文件确认是 0.4.6，不影响功能 |

## 源码修改

3 个补丁：

| 补丁 | 修改文件 | 内容 |
|------|----------|------|
| 0001-Makefile.patch | Makefile | 添加 DESTDIR 支持，$(PREFIX) → $(DESTDIR)$(PREFIX)；修复 install 路径 |
| 0002-config.mk.patch | config.mk | CXX=clang++、CFLAGS="-Wall -ansi -pedantic -O2 -fPIC" |
| 0003-configure.patch | configure (新增) | configure wrapper 脚本，解析 --prefix 并修改 config.mk |

## 依赖版本

- clang 15.0.4 (系统自带)
- 无外部编译依赖（纯 C++ 头文件+源码库）

## 验证结果

```bash
$ voro++ --version
Voro++ version 0.4.5 (July 27th 2012)

$ file /usr/local/bin/voro++
ELF 64-bit LSB executable, ARM aarch64

$ file /usr/local/lib/libvoro++.a
current ar archive (ELF 64-bit LSB relocatable, ARM aarch64)

$ random_points
Container volume : 8
Voronoi volume   : 8
Difference       : -8.88178e-16

$ cell_statistics
Volume              : 7
Surface area        : 21.8284
Total faces         : 7
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| voro++-0.4.6-ohos-aarch64.tar.gz | 910KB | 预编译包（bin/lib/include/man） |
| voro++-0.4.6-ohos-aarch64-debug.tar.gz | 70KB | 调试符号包 |

## 注意事项

- 版本号字符串显示 0.4.5 而非 0.4.6（上游 bug，不影响功能）
- import 示例无法运行（dfsg1 源码包不含外部数据文件）
- voro++ 为静态库，无动态库产物

---
**编译结束**: 2026-06-03 03:26
**最终状态**: published