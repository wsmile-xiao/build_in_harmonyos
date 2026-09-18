# lout

Basser Lout 是 Jeffrey H. Kingston 开发的文档排版系统：声明式 Lout 语言
描述文档结构与内容，由 `lout` 编译器排版输出 PostScript/PDF/纯文本。
一个文档语言 + 编译器的完整系统，含字体（font/）、断字（hyph/）、
字符映射（maps/）、标准包（include/）与数据（data/）运行时树。

## 功能概述

- 声明式文档语言：目标文档（报告/书籍/信函/幻灯）由标准包组合
- 输出后端：PostScript（默认，`-EPS` 封装 PS）、PDF（`-Z`）、
  纯文本（`-p`）
- 多遍解析（`-r<n>`）：交叉引用/索引/目录在后续遍收敛
- 伴随工具 `prg2lout`：将任意程序清单转成带语法高亮的 Lout 文档

## OHOS 适配要点

- **构建系统**: 单一 GNU makefile（非 autotools、无 configure），
  通过 make 变量注入 CC/BINDIR/LOUTLIBDIR/DESTDIR
- **补丁（3.43.4）**: catgets 哨兵检查 —— `catopen()` 失败返回
  `(nl_catd)-1`（POSIX），lout 的 `condcatgets` 宏只判 NULL，OHOS
  musl 的 `catgets()` 解引用无效描述符直接 SIGSEGV（glibc 容错），
  参照上游 3.43 对 `catclose()` 的同类修复加哨兵（DRAFT-E577）
- **运行时树解析**: `$LOUTLIB` > argv[0] 相对 `../../lib` > 编译期
  `LIB_DIR`；包内布局为 `res/lib`，消费端必须设 `LOUTLIB`
- **测试**: 上游 `make test` 需 lout-3.40 参照二进制（OHOS 无）；
  可运行核心（`-r3 all` 全量用户手册 3 遍格式化，PS + 纯文本）在
  配方 `build()` 中执行，消费者测试见 test_package/
- **许可证**: GPL-2.0-only
- **上游源**: 作者 GitHub 仓库 william8000/lout（Savannah/SourceForge
  仅到 3.40，作者个人主页已失效）

## 依赖关系

- **编译依赖**: 无（纯 C89/C99，零外部库）
- **运行依赖**: musl libc（系统自带；locale catalogs 可选）

## 源码结构（3.43.4）

| 文件/目录 | 说明 |
|------|------|
| z01.c–z52.c | 排版引擎（按模块编号拆分的单遍编译器） |
| prg2lout.c | 程序清单转换工具 |
| include/ | 标准包（doc/report/book 等 Lout 库） |
| font/, hyph/, maps/, data/ | PostScript 字体指标、断字模式、字符映射、运行时数据 |
| doc/ | 用户/设计/专家手册源（也是 make test 的测试语料） |
| makefile | 唯一构建入口 |

## 参考资料

- 官方仓库: https://github.com/william8000/lout
- Savannah 项目页: https://savannah.nongnu.org/projects/lout/
- 许可证: GPL-2.0-only（源码 COPYING）
