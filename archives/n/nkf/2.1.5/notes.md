# nkf 2.1.5 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-08-07
- 编译器: clang/clang++
- 状态: built

## 编译步骤

nkf 使用简单 Makefile 构建，无 configure 步骤：

```bash
# 应用补丁（修复 man 页安装路径）
patch -p1 < patches/0001-Makefile.patch

# 编译
make CC=clang CFLAGS="-fPIC -O2 -Wall" MKDIR="mkdir -p" -j1

# 安装到 staging 目录
make install prefix=$TEST_PREFIX CC=clang CFLAGS="-fPIC -O2 -Wall" MKDIR="mkdir -p"

# 运行测试
make test
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | man 页安装到 prefix/man 而非标准路径 | Makefile 硬编码 man 路径 | 补丁修改为 prefix/share/man |
| 2 | conan create 中 make 找不到 Makefile | basic_layout 将构建目录设为 build-release 子目录 | conanfile.py 中使用 cwd=self.source_folder |
| 3 | 源码 URL 使用 Debian 镜像而非官方源 | 历史使用 Debian URL | 改为 GitHub 官方源 (R39) |

## 源码修改

- patches/0001-Makefile.patch: 修改 Makefile 中 man 页安装路径从 $(prefix)/man 到 $(prefix)/share/man

## 依赖版本

无外部依赖，纯 C 实现。

## 验证结果

```bash
$ nkf --version
Network Kanji Filter Version 2.1.5 (2018-12-15)

$ make test
All tests are succeeded.
```

## 注意事项

- nkf 是命令行工具（application），非库（library）
- 构建产物为 bin/nkf 可执行文件
- 上游测试使用 perl test.pl，覆盖编码转换、MIME 解码等功能
- conanfile.py 中需使用 cwd=self.source_folder 运行 make
---

**编译结束**: 2026-08-07
**最终状态**: built
