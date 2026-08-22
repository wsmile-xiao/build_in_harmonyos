# libedit 20240817 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-22
- 编译器: clang / clang++ (OHOS aarch64)
- 状态: built

## 编译步骤

libedit 使用 autotools 构建系统，通过 conanfile.py 自动执行：
1. 下载源码: `http://thrysoee.dk/editline/libedit-20240808-3.1.tar.gz`
2. 应用 3 个有效补丁（config.guess、config.sub、sys.h）; chartype.h 改用 -D__STDC_ISO_10646__ CFLAGS
3. 运行时 patch：configure umask 077→022、terminal.c feature-based termcap decl (HAVE_NCURSES_H && !HAVE_TERMCAP_H)
4. `./configure --enable-static --disable-shared --disable-examples`
5. `make -j1`
6. `make install`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 知识库 |
|---|------|------|----------|--------|
| 1 | /tmp 只读导致 configure shell 失败 | /tmp 是 erofs 只读文件系统 | 设置 TMPDIR 到可写目录 | E011/HMDFS |
| 2 | config.status 无法创建临时文件 | umask 077 创建 mode 0700 目录，HMDFS 无法写入 | patch configure: umask 077→022 | E011/HMDFS |
| 3 | 系统 ncurses 找不到 | AC_CHECK_LIB(ncurses) 需 libncurses.a，系统只有 libncursesw.a | 创建 libncurses.a → libncursesw.a 符号链接 | — |
| 4 | termcap 函数未声明 | OHOS ncurses 头文件无 tgetent/tgoto/tputs 声明 | patch terminal.c: feature-based decl (HAVE_NCURSES_H && !HAVE_TERMCAP_H) | — |
| 5 | test_package 链接失败 | 未传递 ncurses 链接库 | CMakeLists.txt 添加 find_library(ncursesw) | — |
| 6 | chartype.h wchar_t 检查失败 | OHOS 未定义 __STDC_ISO_10646__ | -D__STDC_ISO_10646__ CFLAGS（替代移除的 0010 补丁，避免 R8 违规） | — |
| 7 | configure 无法识别 OHOS | config.guess/sub 未包含 OHOS 条目 | 补丁添加 aarch64-unknown-linux-ohos 支持 | — |

## 源码修改

### 有效补丁（3 个，直接应用到源码包）
- `0002-config.guess.patch` — 添加 OHOS 系统检测
- `0003-config.sub.patch` — 添加 ohos 操作系统支持
- `0016-src-sys.h.patch` — OHOS 兼容

### 运行时 patch（conanfile.py build() 中执行）
- `configure`: umask 077→022（HMDFS 临时目录权限修复）
- `src/terminal.c`: feature-based termcap decl（HAVE_NCURSES_H && !HAVE_TERMCAP_H）
- `libncurses.a` → `libncursesw.a` 符号链接

### 排除的补丁（目标文件不在源码包中）
- 0001: AI review 分类文件，非真实补丁
- 0004-0006: 目标 doc/*.3/.7/.5（新文件），源码有 doc/*.3.roff
- 0007-0009: 目标 examples/fileman/tc1/wtc1（新 libtool 包装），源码有 .c 文件
- 0011-0015, 0017: 目标生成头文件（vi.h, emacs.h, common.h, fcns.h, func.h, help.h），不在源码包中

## 上游测试用例核验

| 检查项 | 结果 |
|--------|------|
| test/ 目录 | ❌ 不存在 |
| tests/ 目录 | ❌ 不存在 |
| Makefile.am check target | ❌ 无 check/test 目标 |
| configure.ac test macros | ❌ 无测试相关宏 |
| ctest -N | ❌ 无 CMakeLists.txt |
| make -n check | ❌ 无 check 目标 |
| examples/ 程序 | 仅交互式示例（tc1, wtc1, fileman, fuzz1），非自动化测试 |
| INSTALL 文件 | 通用 autotools 模板，非 libedit 特有 |

**结论：上游无自动化测试用例。** 上游测试用例通过率：**0/0（N/A，上游无测试用例）**。

## 验证结果

| 验证项 | 结果 |
|--------|------|
| conan create | ✅ PASS |
| test_package | ✅ 4/4（100%）：el_init, el_end, history_init, history_end |
| conan-verify G0-G4 | ✅ 全部 PASS |
| finish | ✅ EXIT_CODE=0（status=built），非核心步骤有警告（SUMMARY.md 生成、packaging/ 未创建） |

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| ncurses（系统） | 6.4 | 终端处理（tgetent, tgetflag, tputs 等） |

## 注意事项

- libedit 版本号使用日期格式 (YYYYMMDD)，源码实际取自 libedit-20240808-3.1.tar.gz
- 上游无自动化测试用例，仅提供 examples/ 下的交互式示例程序
- test_package 补充了消费者级 API smoke test（4 个断言，全部通过）
- 编译时禁用示例程序（--disable-examples）以减少终端依赖
- 路径 A，复用 E011/HMDFS 类知识，不申请路径 B
- finish 非核心警告（SUMMARY.md 生成、packaging/ 缺失）不影响构建结果

---

**编译结束**: 2026-07-22
**最终状态**: built
---

**编译结束**: 2026-07-22 22:58
**最终状态**: built
