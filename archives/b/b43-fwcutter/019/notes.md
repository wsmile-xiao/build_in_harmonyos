# b43-fwcutter 019 适配笔记

## 编译环境
- 构建系统: makefile（简单 Makefile，非 autotools，无 configure 脚本）
- 编译日期: 2026-06-30
- 编译器: clang 15.0.4 / clang++
- 状态: published

## 编译步骤

1. **下载源码**: 从 https://bues.ch/b43/fwcutter/b43-fwcutter-019.tar.bz2 下载（SSL 证书问题需 curl -kSL）
2. **检查构建系统**: 源码目录仅有 Makefile，无 configure 脚本，判定为简单 Makefile 项目
3. **编译**: `make CC=clang CFLAGS="-fPIC -O2 -std=c99 -Wall -pedantic -D_BSD_SOURCE -DFWCUTTER_VERSION_=019" LDFLAGS="-static" -j1`
4. **安装**: `make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX`
5. **验证**: `b43-fwcutter --version` 输出 "b43-fwcutter version 019"

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 下载失败 SSL CERTIFICATE_VERIFY_FAILED | 鸿蒙系统 CA 证书不完整 | 使用 `curl -kSL` 手动下载到 $TMPDIR/builds/ |
| 2 | Makefile install 目标使用 `-o 0 -g 0`（root 权限） | 原始 Makefile 假设 root 安装 | 修改 Makefile 移除 `-o 0 -g 0`，添加 `$(DESTDIR)` 支持 |
| 3 | conanfile.py 模板基于 autotools 但项目用 Makefile | conan-init 默认生成 autotools 模板 | 改用 `self.run("make ...", cwd=src)` 方式构建 |
| 4 | conan create 时 make 找不到 Makefile | `self.run()` 默认在 build 目录执行 | 添加 `cwd=src` 参数指定源码目录 |
| 5 | test_package 找不到二进制 | 使用 PATH 查找失败 | 改用 `self.dependencies["b43-fwcutter"].package_folder` 构造完整路径 |
| 6 | test_package `--help` 返回 255 | 源码中 --help 走 out_usage 返回 -1 | 改用 `--version`（返回 0） |
| 7 | conandata.yml SHA256 为占位符 | conan-init 自动生成时未计算 | 手动替换为实际 SHA256 |

## 源码修改

- **补丁文件**: `patches/0001-Makefile.patch`（+5/-5）
- **修改文件**: Makefile
- **修改内容**:
  - 移除 install 目标中的 `-o 0 -g 0`（root 用户/组归属）
  - 在安装路径前添加 `$(DESTDIR)` 支持 staging 安装
  - 去除行尾多余空格（dep 规则行）

## 依赖版本

- 无第三方依赖（b43-fwcutter 仅依赖标准 C 库）
- 编译器: clang 15.0.4
- 构建工具: GNU Make 4.4.1

## 验证结果

```bash
$ b43-fwcutter --version
b43-fwcutter version 019
# 退出码: 0

$ readelf -d b43-fwcutter
There is no dynamic section in this file.
# 完全静态链接，R26 合规

$ file b43-fwcutter
ELF executable, 64-bit LSB arm64, static, not stripped
```

## 注意事项

- b43-fwcutter 是终端工具，必须静态链接（R26），编译时使用 `LDFLAGS=-static`
- Makefile 默认 `CC=cc`，鸿蒙上无 cc 软链接，必须显式指定 `CC=clang`（E001）
- `--help` 退出码为 255（源码返回 -1），`--version` 退出码为 0，测试时使用 `--version`
- conanfile.py 中使用 `replace_in_file` 在构建时修改 Makefile，无需额外补丁文件即可在 conan create 中复现

---

**编译结束**: 2026-06-30 17:17
**最终状态**: published
