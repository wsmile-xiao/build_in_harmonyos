# E636 — autotools 把生成的 PDF 文档列进 BUILT_SOURCES，out-of-tree/无 LaTeX 构建在 make all 第一步即失败

## 错误特征

`make all` 的第一条输出就是构建 PDF 文档并立即失败：

```text
qd/2.3.23-dfsg.1: RUN: make -j1
make -C docs qd.pdf
make[1]: Entering directory '/…/b/build-release'
make[1]: *** docs: No such file or directory.  Stop.
make[1]: Leaving directory '/…/b/build-release'
make: *** [Makefile:1010: docs/qd.pdf] Error 2
```

另一种同源形态（源码树有 docs/ 但没有 LaTeX 时）是 `pdflatex: not found` /
`texi2dvi: command not found` 之类文档工具链报错。

## 触发条件

- 构建系统: autotools（automake 生成的 Makefile.in / Makefile）
- 阶段: `make`（`all` 目标的第一步，先于任何编译输出）
- 上游 `Makefile.am` 存在 `BUILT_SOURCES = docs/xxx.pdf`（automake 语义：`all`
  之前强制先建 BUILT_SOURCES），通常同时把该 PDF 列进 `dist_doc_DATA`
- Conan/AutotoolsToolchain 默认 **out-of-tree** 构建：构建目录里没有 `docs/`
  子目录，`make -C docs` 直接 `No such file or directory`
- 设备与 CI 都没有 LaTeX 工具链——即使手工补出 docs/ 目录，PDF 也造不出来

## 根因分析

上游维护者的发布流程是 in-tree 构建（源码树自带 `docs/`），`BUILT_SOURCES`
能正常工作；这个假设对 out-of-tree 构建（Conan、cmake 外部构建）和缺少
LaTeX 的干净环境不成立。`dist_doc_DATA` 还把 PDF 挂到 `install-data` 上，
即使绕过构建阶段，`make install` 也会因 `cannot stat 'docs/xxx.pdf'` 失败。
automake 对 `dist_*DATA` 的安装规则有 `$(srcdir)/` 回退
（`if test -f "$$p"; then d=; else d="$(srcdir)/"; fi`），所以**源码树里已存在**
的文件可以正常安装，只有"需要现生成"的 PDF 是死结。

## 解决方案

### 推荐方案

补丁生成的 `Makefile.in`（configure 会用它重新生成 Makefile）：`BUILT_SOURCES`
置空 + 从 `dist_doc_DATA` 移除 PDF（保留 `README` 等源码树自带文件）：

```patch
--- a/Makefile.in
+++ b/Makefile.in
@@ -392,8 +392,8 @@
 SUBDIRS = src include tests fortran
 pkgconfigdir = $(libdir)/pkgconfig
 pkgconfig_DATA = qd.pc
-BUILT_SOURCES = docs/qd.pdf
-dist_doc_DATA = README docs/qd.pdf
+BUILT_SOURCES =
+dist_doc_DATA = README
```

先在源码树确认两条赋值的确切写法再写补丁：
`grep -n "BUILT_SOURCES\|dist_doc_DATA" Makefile.am Makefile.in`。

### 回退方案

上游若提供 `--disable-doc` / `--without-docs` 类开关，优先用配方
`configure_args` 关闭，不打补丁。

### 禁止做法

- ❌ `touch docs/qd.pdf` / `echo > docs/qd.pdf` 造一个假文件顶替安装清单——
  安装进包的是损坏产物，且掩盖了文档从未构建的事实。

## 验证

```bash
# 1) 确认补丁后 BUILT_SOURCES 不再引用 docs
grep -n "BUILT_SOURCES" <build-dir>/Makefile     # 应为 BUILT_SOURCES =
# 2) make all 不再出现 make -C docs，且 check/安装正常
make -j1 && make check -j1 && make install DESTDIR=/tmp/inst
```

## 关联条目

- 场景同源（发布假设与 CI 环境不符）：E052/E060/E112/E114（config.status
  临时目录 umask 0700 在 HMDFS 上不可写——同一任务的另一个必现失败点）

## 来源

qd 2.3.23-dfsg.1 鸿蒙适配（2026-09-21）：`make all` 第一步
`make -C docs qd.pdf` 失败，补丁 `0002-Makefile-in-skip-pdf-doc.patch` 后全绿。
