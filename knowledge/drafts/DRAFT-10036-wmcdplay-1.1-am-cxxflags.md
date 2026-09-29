# DRAFT-10036: automake 的 AM_CFLAGS 不覆盖 C++ 源文件（须补 AM_CXXFLAGS）

- 条目主题：autotools 项目里 C++ 源（`.cc`/`.cpp`）收不到 `AM_CFLAGS` 注入的 pkg-config 头文件路径。
- 状态：草稿（待知识库主编审核，拟提升编号 Exxx）
- 关联软件：wmcdplay 1.1；适用所有"C++ 源 + AM_CFLAGS 注入依赖"的 autotools 包。

## 错误特征
```
fatal error: 'X11/X.h' file not found
fatal error: 'X11/xpm.h' file not found
```
且 `make V=1` 显示编译驱动是 `clang++`/`g++`，命令行里**没有任何 `-I`**。

## 根因
automake 内建规则把 `AM_CFLAGS` 只传给 C 编译；C++ 编译走 `AM_CXXFLAGS`。上游
`Makefile.am` 声明 `AM_CFLAGS = $(x11_CFLAGS) ...` 而源文件是 C++ 时，依赖头文件
搜索路径完全丢失。

## 修复
```make
AM_CXXFLAGS = $(x11_CFLAGS) $(xpm_CFLAGS) $(xext_CFLAGS)
```
（与 AM_CFLAGS 同值；自举后用 `make V=1` 确认 C++ 命令行出现 `-I<dep>/include`。）

## 判定技巧
报错的编译驱动带 `++` 而命令行缺 `-I` ⇒ 基本就是本条，而不是 pc 文件坏。

## 关联
E490（辅助脚本可执行位）、DRAFT-10035（OHOS autotools 自举）。
