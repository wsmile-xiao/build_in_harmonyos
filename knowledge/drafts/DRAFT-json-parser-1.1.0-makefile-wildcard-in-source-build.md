# DRAFT — json-parser 1.1.0：Makefile 使用 `$(wildcard *.c)` 的库必须源内构建（conan out-of-source 下 json.o 缺失）

## 问题

`conan create`（Autotools 或裸 Makefile 配方）编译 json-parser 1.1.0 时，
`llvm-ar rcs libjsonparser.a json.o` 报 `json.o: No such file or directory`，
实际原因不是归档命令本身，而是编译阶段根本没有生成 json.o。

## 根因

json-parser 的 `Makefile.in` 使用：

```make
SRCS = $(wildcard *.c)
OBJS = $(SRCS:.c=.o)
```

`$(wildcard *.c)` 在 make 的**当前工作目录**展开。Conan 默认 out-of-source 构建
（`build-release/` 子目录），make 运行在 build 目录而 .c 源文件在 source 目录，
`$(wildcard *.c)` 展开为空 → OBJS 为空 → 归档规则里的字面量 `json.o` 从未被编译，
llvm-ar 自然找不到。这是"配方构建目录与源码目录分离"与"Makefile 用通配符隐式
取源文件"的组合问题，不是归档工具本身的问题。

## 方案

在配方 `layout()` 中强制源内构建：

```python
def layout(self):
    basic_layout(self)
    self.folders.build = "."
```

使 make 在 source 目录运行，`$(wildcard *.c)` 正常展开。这与既有配方
abc/abduco 等（同样 `self.folders.build = "."`）的处理一致。

## 验证

- 修复前：`conan create` → `llvm-ar: error: json.o: No such file or directory`
- 修复后：`conan create` 编译 `json.c` → 生成 `libjsonparser.a` / `.so`，test_package 通过；
  本地 W3（build_and_test.sh）L0-L5 全部通过

## 适用边界

- 适用于 Makefile 用 `$(wildcard *.c)`（或类似相对当前目录通配）取源文件的库；
- 适用于 `conanfile.py` 使用 `basic_layout` 的配方；
- 若 Makefile 支持 VPATH / out-of-source（automake 等），无需此改动。

## 反例 / 限制

- 不要对所有 autotools 库一律源内构建——automake 生成的 Makefile 支持
  out-of-source，强制 `.` 反而污染源码目录；
- 判定依据：错误必须是 `llvm-ar`/`ar` 报缺 .o 且日志中确实没有对应的
  `clang -c xxx.c` 编译行，才能认定是 wildcard 取源问题。

## 查重差异

- E519（install-data-am 相对路径）同样是 out-of-source 问题，但发生在
  **安装阶段**（`$(EXTRA_DIST)` 相对路径），且方案是改 Makefile 用 `$(srcdir)`；
  本候选是**编译阶段** wildcard 取源为空，方案是配方侧 `folders.build = "."`，不同。
- 官方图库与草稿区均无"Makefile `$(wildcard *.c)` 需源内构建"条目，等价命中不存在。
