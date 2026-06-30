# libdotconf 1.4.1-r0 适配笔记

## 编译环境
- 构建系统: autotools (configure.ac, needs autoreconf -fi)
- 编译日期: 2026-06-02
- 编译器: clang 15.0.4 / clang++
- 状态: published

## 编译步骤

1. 下载源码: GitHub codeload (williamh/dotconf v1.4.1 tag)
2. 源码为 autotools 项目，但 tarball 不包含 generated configure 脚本
3. `autoreconf -fi` 生成 configure（需要先手动复制 ltmain.sh）
4. sed 修复 configure: HMDFS setgid tmp dir fix (replace mktemp -d with mkdir)
5. `./configure --prefix=$DEFAULT_PREFIX`
6. `make -j1` → 编译 libdotconf.so.0.0.1 + libdotconf.a
7. `make install DESTDIR=$TEST_PREFIX` → staging 安装
8. `make check` → PASS (无正式 test suite)
9. `make install` → 本地安装到 DEFAULT_PREFIX
10. `pkg-config --modversion dotconf` → 1.4.1 ✅

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure tmp dir creation "Permission denied" | HMDFS setgid: mktemp -d creates dirs with `drwx--S---` | Replace mktemp -d with mkdir in configure (inherits parent setgid perms) |
| 2 | autoreconf -fi: ltmain.sh placed at wrong path | libtoolize defaults to `../..` | Manually copy ltmain.sh to project root |
| 3 | init-build nested source detection error | Script misidentified nested source | Manually re-extract tarball |

## 补丁策略说明

原始 tarball 不包含 configure/Makefile.in 等构建文件。这些文件由 `autoreconf -fi` 从系统工具链（automake 1.16.5、autoconf 2.72、libtool 2.4.7）复制生成。系统的 config.guess/config.sub 已包含 OpenHarmony 平台支持，无需额外补丁。

唯一需要修改的是 configure 中的 HMDFS mktemp 权限问题，通过 post_autoreconf sed 命令修复（见 manifest.yaml）。

## 源码修改

- **configure** (line 15255-15264): HMDFS setgid fix — replace `mktemp -d "./confXXXXXX"` block with simple `mkdir "$tmp"`
  - 修复方式: sed 命令（post_autoreconf），非补丁文件

## 依赖版本

- autotools: autoconf 2.72, automake 1.16.5, libtool 2.4.7
- clang: 15.0.4
- make: GNU Make 4.4.1

## 验证结果

- 25/25 功能断言全部通过 ✅
- 动态库 (.so) 链接运行正常 ✅
- 静态库 (.a) 链接运行正常 ✅
- pkg-config 元数据正确 ✅
- ELF 签名完成 ✅

## 注意事项

- 此项目在 GitHub 上名为 "dotconf"，但编译名称为 "libdotconf"
- 版本号格式 1.4.1-r0: r0 是 recipe revision，源码版本为 1.4.1
- G0 干净构建验证已知限制：原始 tarball 无 configure，需 autoreconf -fi 生成

---

**编译结束**: 2026-06-02 10:35+00
**最终状态**: published