# inform6 6.44-r3 适配笔记

## 编译环境
- 构建系统: makefile（纯Makefile，无configure脚本）
- 编译日期: 2026-06-11 / 收尾: 2026-06-12
- 编译器: clang/clang++
- 状态: published

## 编译步骤

inform6使用纯Makefile构建，没有configure脚本。需要手动修改Makefile后编译：

```bash
cd $BUILD_SRC_DIR
# Makefile已预先修改以支持DESTDIR模式、PWD修复、TEMPDIR适配等
make -j1 CC=clang PREFIX=$DEFAULT_PREFIX
make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX
```

注意：鸿蒙平台没有独立的`install`命令，需先创建符号链接：
```bash
ln -s ginstall /storage/Users/currentUser/usr/local/bin/install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | make install DESTDIR模式不生效 | Makefile原版不支持DESTDIR | 修改Makefile，将DESTDIR加入BINDIR/SHAREDIR/MANDIR路径前缀 |
| 2 | TEMPDIR硬编码为/tmp | 鸿蒙/tmp只读(E002) | 将TEMPDIR改为 `?=` 赋值，尊重$TMPDIR环境变量(R10) |
| 3 | uname -s返回HarmonyOS | 鸿蒙内核名称不同 | Makefile else分支已正确处理，-DUNIX标志正确应用 |
| 4 | G0验证无法运行configure | 纯Makefile项目没有configure脚本 | 添加configure wrapper脚本（仅exit 0），生成补丁0002-configure-wrapper.patch |
| 5 | G0验证make编译demo失败 | Makefile使用$(PWD)引用编译器路径，PWD环境变量在subprocess中未更新 | 将`$(PWD)/$(BINNAME)`改为`./$(BINNAME)` |
| 6 | install-contrib双重DESTDIR | install-contrib规则使用$(DESTDIR)$(BINDIR)但BINDIR已含DESTDIR | 移除显式$(DESTDIR)前缀，改为直接使用$(BINDIR) |
| 7 | 鸿蒙无install命令 | coreutils使用ginstall而非install | 创建install→ginstall符号链接 |

## 源码修改

补丁1: `0001-makefile-destdir-ohos.patch`

主要修改内容:
1. 新增 `DESTDIR ?=` 变量声明
2. BINDIR/SHAREDIR/MANDIR 加入 `$(DESTDIR)` 前缀
3. TEMPDIR 从 `= /tmp` 改为 `?= /tmp`（R10适配）
4. `$(PWD)/$(BINNAME)` 改为 `./$(BINNAME)`（修复subprocess PWD环境变量问题）
5. install-compiler/install-alt/install-contrib/install-punywrapper 规则中移除显式 `$(DESTDIR)` 前缀（因DESTDIR已融入路径变量）
6. install-contrib规则添加 `install -d` 创建目录步骤

补丁2: `0002-configure-wrapper.patch`

添加configure wrapper脚本，内容为：
```sh
#!/bin/sh
# configure wrapper for inform6 - pure Makefile project
# 仅exit 0以满足G0干净构建验证系统要求
for arg in "$@"; do
    case "$arg" in
        --prefix=*) PREFIX="${arg#--prefix=}" ;;
        --help|-h)  echo "inform6 configure wrapper (Makefile project)" && exit 0 ;;
    esac
done
echo "configure: inform6 is a pure Makefile project (no configure needed)"
echo "configure: PREFIX=${PREFIX:-/usr/local}"
exit 0
```

## 依赖版本

无外部依赖。inform6是独立的Inform 6编译器。

## 验证结果

### Staging验证（DESTDIR模式）
```bash
$ $TEST_PREFIX/$DEFAULT_PREFIX/bin/inform-6.44
Inform 6.44 for Unix (11th September 2025)
# ELF 64-bit LSB arm64, dynamic, libc.so, 612800字节
```

### 本地安装验证（无DESTDIR）
```bash
$ /storage/Users/currentUser/usr/local/bin/inform --version
Inform 6.44 for Unix (11th September 2025)
```

### 功能编译测试
```bash
$ inform +std std-demos/advent.inf test-advent.z5
Inform 6.44 for Unix (11th September 2025)
# 输出: test-advent.z5 (152064字节 Z-machine故事文件)
```

### G0干净构建验证
```bash
$ python3 ohc-run.py clean-verify inform6 6.44-r3
✅ configure 成功 (wrapper脚本exit 0)
✅ make 成功 (21源文件+7demo+8tutorial+52puny测试全部编译)
✅ make install DESTDIR 成功 (9 bin, 27 lib)
✅ G0 干净构建验证通过
```

### make check: N/A（无测试套件）

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| inform6-6.44-r3-ohos-aarch64.tar.gz | 7.4MB | 预编译包（编译器+标准库+PunyInform+文档+demo） |
| inform6-6.44-r3-ohos-aarch64-debug.tar.gz | 152KB | debug symbols包 |

预编译包内容 (317文件):
- bin/: inform-6.44 (620KB ELF), punyinform.sh + 符号链接
- share/inform/std/: Standard Library (lib + include + demos + tutor)
- share/inform/punyinform/: PunyInform Library (lib + howto + tests + docs)
- man/man1/inform.1
- lib/external/

## 注意事项

- inform6无configure脚本，所有平台适配需直接修改Makefile
- 纯Makefile项目DESTDIR模式需手动将DESTDIR融入路径变量，不能仅在install目标加DESTDIR
- DESTDIR融入路径变量后，所有install规则中不能再用$(DESTDIR)$(BINDIR)等显式双重前缀
- TEMPDIR必须用 `?= ` 而非 `= ` 以尊重$TMPDIR（R10铁律）
- 纯Makefile项目需添加configure wrapper以满足G0验证要求
- Makefile中引用编译器路径应使用`./$(BINNAME)`而非`$(PWD)/$(BINNAME)`，避免subprocess PWD环境变量问题
- 鸿蒙平台需创建install→ginstall符号链接（coreutils的install命令名为ginstall）
- 编译产物包括编译器二进制(inform)和标准库/演示文件(std/punyinform)

---
**编译结束**: 2026-06-12
**最终状态**: published