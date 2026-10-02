# DRAFT: Makefile.am 相对路径（-Icompat 等）在 VPATH 构建下解析错位

- Status: UNMATCHED
- Category: build-system / autotools / vpath
- Keywords: VPATH, AM_CFLAGS, -Icompat, sys/tree.h file not found, Makefile.am, relative include, out-of-tree build, Conan basic_layout
- Related: E041

## 现象（trickle-1.08 真机 r20，2026-10-01）

trickle 源码自带 `compat/sys/tree.h`，`Makefile.am` 写了
`AM_CFLAGS = -Wall -Icompat ...`。Conan（basic_layout，out-of-tree）在
`build-release/` 子目录执行 make 时：

```
clang ... -Wall -Icompat ... -c trickled.c
trickled.c:22: fatal error: 'sys/tree.h' file not found
```

`compat/` 明明在源码根目录存在。

## 根因

`-Icompat` 是**相对当前工作目录**的包含路径。in-tree 构建时 make 在
源码根执行，解析到 `<src>/compat`；VPATH/out-of-tree 构建时 make 在
`build-release/` 执行，解析到 `build-release/compat`（不存在）。相对
路径在 AM_CFLAGS/AM_CPPFLAGS 中是隐式 in-tree 假设。

## 方案

configure 之后、make 之前，把生成的 Makefile 中相对路径替换为源码树
绝对路径（配方内即可，无需上游补丁）：

```python
mk = os.path.join(self.build_folder, "Makefile")
text = open(mk).read()
if "-Icompat" in text:
    abs_compat = os.path.join(self.source_folder, "compat")
    open(mk, "w").write(text.replace("-Icompat", f"-I{abs_compat}"))
```

更根本的上游级修法是 Makefile.am 用 `$(srcdir)/compat`，但老项目多用
相对路径，配方侧替换更省事且不引入平台特判补丁。

## 验证

r20 该错误即致命；r21 应用替换后编译全链通过（r23 真机 L0-L5 全绿，
trickle/trickled/tricklectl 及两个 .so 模块全部产出）。

## 复用面

所有"源码树带 compat/ 或本地 include 目录 + AM_CFLAGS 相对 -I"的老
autotools 项目（BSD 系工具尤其常见：trickle、bsd-compat 类）在 Conan/
VPATH 构建下都会踩。编译期报 `xxx.h file not found` 但文件确实存在时，
优先检查 make 命令行里的相对 -I 与实际 make cwd。
