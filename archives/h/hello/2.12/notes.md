# hello 2.12 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-21
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. **初始化编译环境**
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py init-build hello 2.12 --url=file://$HOME/tmp/hello-2.12.tar.gz
   ```

2. **修改 config.guess**
   - 添加 HarmonyOS 系统识别分支（第 180-189 行）
   - 添加输出和退出语句（echo "$GUESS"; exit ;;）

3. **修改 config.sub**
   - 在 kernel-os 白名单中添加 linux-ohos*（第 1748 行）

4. **修改 configure**
   - 将 umask 077 改为 umask 022（解决 HMDFS UID 映射问题）

5. **运行 configure**
   ```bash
   ./configure --prefix=/storage/Users/currentUser/usr/local
   ```

6. **手动编译缺失的 .o 文件**
   ```bash
   make lib/getopt.o lib/getopt1.o lib/error.o
   ```

7. **重新打包静态库**
   ```bash
   rm lib/libhello.a
   llvm-ar rcs lib/libhello.a lib/*.o
   ```

8. **编译程序**
   ```bash
   gcc -g -O2 -o src/hello src/hello.o lib/libhello.a
   ```

9. **手动安装**
   ```bash
   mkdir -p $TEST_PREFIX/$DEFAULT_PREFIX/bin
   ginstall -c src/hello $TEST_PREFIX/$DEFAULT_PREFIX/bin/hello
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别系统类型 | 补丁脚本未添加输出和退出语句 | 手动在第 188-189 行添加 `echo "$GUESS"; exit ;;` |
| 2 | config.sub 三元组验证失败 | kernel-os 白名单缺少 linux-ohos* | 在第 1748 行添加 `linux-ohos*` |
| 3 | configure 创建临时目录失败 | HMDFS UID 映射 + umask 077 导致权限问题 (E011) | 修改 configure 中的 umask 077 为 umask 022 |
| 4 | make 失败（缺少 makeinfo） | texinfo 未预装 | 跳过文档编译 |
| 5 | 链接失败（rpl_optarg 等符号未定义） | gnulib 替换函数未编译打包 | 手动编译 getopt.o、getopt1.o、error.o 并重新打包静态库 |

## 源码修改

应用了 4 个补丁：
- **0001-Makefile.in.patch**: 注释 info_TEXINFOS、INFO_DEPS、DVIS、PDFS、PSS、HTMLS、TEXINFOS 等文档相关变量，跳过文档构建（解决 makeinfo 缺失问题）
- **0002-build-aux-config.guess.patch**: HarmonyOS 系统识别
- **0003-build-aux-config.sub.patch**: linux-ohos 三元组验证
- **0004-configure.patch**: umask 修改（E011 解决方案）

**R6 规范说明**：
- `doc/stamp-vti` 和 `doc/version.texi` 是 make 自动生成的文件，不应作为补丁
- 源码包已包含这些文件，Makefile.in.patch 已注释所有文档构建目标，构建时不会重新生成

## 依赖版本

- clang 15.0.4
- automake 1.17
- autoconf 2.72
- GNU make 4.4.1
- LLVM ar (llvm-ar)

## 验证结果

```bash
$ hello --version
hello (GNU Hello) 2.12.1-6fe9
Copyright (C) 2020 Free Software Foundation, Inc.
License GPLv3+: GNU GPL version 3 or later <https://gnu.org/licenses/gpl.html>
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.

Written by Karl Berry, Sami Kerola, Jim Meyering,
and Reuben Thomas.

$ hello
Hello, world!

$ hello --greeting="Hello, OpenHarmony!"
Hello, OpenHarmony!
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| hello-2.12-ohos-aarch64.tar.gz | 85KB | 预编译包（包含 hello 可执行文件） |
| 0001-Makefile.in.patch | 10KB | 跳过文档构建补丁（注释 info_TEXINFOS、INFO_DEPS、DVIS、PDFS、PSS、HTMLS、TEXINFOS 等） |
| 0002-build-aux-config.guess.patch | 1KB | HarmonyOS 系统识别补丁 |
| 0003-build-aux-config.sub.patch | 3KB | linux-ohos 三元组验证补丁 |
| 0004-configure.patch | 1KB | umask 修改补丁 |

**注意**：已移除违规补丁 0005-doc-stamp-vti.patch 和 0006-doc-version.texi.patch（R6 规范）

## 注意事项

1. **makeinfo 缺失解决方案**: texinfo 预编译包不完整（缺少 Texinfo::ModulePath 等 Perl 模块），通过修改 Makefile.in 注释 info_TEXINFOS、INFO_DEPS 等变量跳过文档构建
2. **config.guess 补丁完整性**: 必须包含输出和退出语句，否则会继续执行到错误检测
3. **config.sub kernel-os 白名单**: 必须添加 linux-ohos*，否则三元组验证失败
4. **umask 问题**: HMDFS UID 映射导致的权限问题（E011）是通用问题，所有 autotools 项目都可能遇到
5. **gnulib 替换函数**: 如果 configure 检测到函数不兼容，可能需要手动编译替换版本

---

**编译结束**: 2026-05-21 18:00
**最终状态**: published
**质量门禁**: G0-G4 全部 PASS

## 修复记录（R6 违规修复）

**修复日期**: 2026-05-21

**问题描述**：
- 补丁 0005-doc-stamp-vti.patch 和 0006-doc-version.texi.patch 违反 R6 规范
- 这些文件是 make 自动生成的文件，不应作为补丁提交
- 补丁内容错误，包含环境变量等垃圾内容

**修复措施**：
1. 删除违规补丁文件（0005 和 0006）
2. 清理 .edit-tracker.json 中的 doc/ 文件记录
3. 验证 Makefile.in.patch 正确性（已注释所有文档构建变量）
4. 重新验证补丁应用成功

**验证结果**：
- 补丁数量：4 个（无 doc/ 开头文件）
- 补丁内容：正确（无环境变量等垃圾内容）
- .edit-tracker.json：已清理（只包含源文件）