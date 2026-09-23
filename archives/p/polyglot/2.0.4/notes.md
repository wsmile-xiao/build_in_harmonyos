# polyglot 2.0.4 适配笔记

## 编译环境
- 构建系统: autotools（tarball 自带预生成 configure，2008 年代 config.guess）
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4
- 平台: 鸿蒙 (OpenHarmony) aarch64
- 状态: built

## 编译步骤

1. 下载并解压源码：`python3 $SKILL_ROOT/scripts/ohc-run.py init-build polyglot 2.0.4 --url=https://ftp.debian.org/debian/pool/main/p/polyglot/polyglot_2.0.4.orig.tar.gz`
2. E129 修复：`sed -i 's/umask 077/umask 022/g' configure`（HMDFS setgid + umask 077 → drwx--S--- 临时目录无写权限）
3. `./configure --prefix=$DEFAULT_PREFIX` —— 一次通过（AC_CHECK_LIB 只查 libm）
4. `make -j4` —— 37 个 .c 编译零错误，仅一个警告级提示（2015 年代 C 代码，clang 15 默认非致命）
5. `make install DESTDIR=$TEST_PREFIX` —— staging 安装：bin/polyglot + share/doc/polyglot/* + share/man/man6/polyglot.6
6. 产物验证：`file polyglot` → ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)
7. Conan 配方：conan-init 生成骨架后手写适配（application 类型）
8. 收尾：`python3 $SKILL_ROOT/scripts/ohc-run.py finish polyglot 2.0.4 built`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 阶段 config.status 报 Permission denied（HMDFS setgid + umask 077） | 上游 configure 创建临时目录用 `umask 077`，HMDFS 新目录强制 setgid，生成 `drwx--S---` 连属主都无写权限 | E129 知识命中：`sed -i 's/umask 077/umask 022/g' configure`；配方 build() 内联 sed（与 pv/1.7.24 先例一致，无需 patch 文件） |
| 2 | make install 打印 `cp: bad '644': No such file or directory` | 上游 Makefile.am 用 install 命令风格过旧（`install -c -m 644 'file' 'dest'` 单引号写法与现代 install 兼容性问题），仅影响 doc/man 文件复制打印错误，退出码 0 | 非阻塞：核心产物 bin/polyglot 与全部 doc/man 文件实际均已正确落位（staging 树验证完整） |
| 3 | 上游无 make check 测试套件 | check-am 仅依赖 all-am，无 TESTS 定义 | R34 由 test_package 弥补：三子命令实质断言（make-book/dump-book/merge-book + usage banner） |

## 功能验证（三子命令全部实测通过）

```bash
# make-book：两盘 PGN（Scholar's mate + Fool's mate）→ 96 字节 book
$ polyglot make-book -pgn test.pgn -bin book.bin -min-game 1
3 games. 11 entries. filtering ... 6 entries. all done!  # rc=0, book.bin=96B (6 entries × 16B)

# dump-book -color white（默认输出 book_white.txt）
$ polyglot dump-book -bin book.bin -color white
Dump of "book.bin" for white.
1: 1. e4{100%} e5 2. Qh5{100%} Nc6 3. Bc4{100%} Nf6 4. Qxf7#{100%}

# dump-book -color black
1: 1. f3 e5{100%} 2. g4 Qh4#{100%}

# merge-book
$ polyglot merge-book -in1 book.bin -in2 book2.bin -out merged.bin
skipped 6 entries. done!  # 相同内容合并去重，rc=0

# 无参数：打印 banner（退出码 0）
$ polyglot
PolyGlot 2.0.4 by Fabien Letouzey.
tellusererror POLYGLOT: main(): Can't open config file "polyglot.ini" ...
```

## 依赖版本

- 零 conan 依赖（requirements() 为空；AC_CHECK_LIB 仅 libm，系统 musl 提供）

## test_package 设计说明（R34）

- Python 外部脚本模式（pacvim 先例）：test_polyglot.py 直接执行打包后的 polyglot 二进制
- 断言 1-3（make-book）：rc=0、book.bin 存在且 size>0、size%16==0（Polyglot book 为 16 字节 entry 序列，无魔数头——book_format.html 实证）
- 断言 4-6（dump-book）：white/black 各 rc=0、输出文件含走子记谱（e4/Qxf7# 与 Qh4#）
- 断言 7（merge-book）：rc=0 且 merged.bin 有效（size%16==0）
- 断言 8-9（usage banner）：无参数运行输出含 "PolyGlot" 与 "2.0.4"
- 证据标记：HMBS_TEST_PACKAGE_RESULT: PASS (9/9)

## 备注

- 源码顶层目录名是 polyglot-2.0.4.orig（Debian pool 命名），conan get(strip_root=True) 自动剥离首层
- pipex_win32.c 被编译但内部有平台条件守卫，不影响 OHOS
- make check 无上游测试，不适用（已记录）
---

**编译结束**: 2026-09-03 14:41
**最终状态**: built
