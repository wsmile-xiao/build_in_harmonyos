# E649 草稿：GNU make 命令行 CC 覆盖会静默丢弃目标级 `CC +=` 追加

> 状态：草稿（DRAFT，待人工审核）｜来源：scalpel 1.60-git20240110.6960eb2（nolaforensix/scalpel-1.60 commit 6960eb2）OHOS aarch64 适配（2026-09-21）

## 问题

为 raw Makefile 工程（无 configure）写 Conan 配方时，按惯例传命令行
`CC=<clang>` 注入交叉编译器后，scalpel 编译失败：

```
helpers.c:64:14: error: incompatible integer to pointer conversion
    assigning to 'char *' from 'int' [-Wint-conversion]
```

错误点（helpers.c 的 `basename` 赋值）与真正根因（make 变量语义）相隔一层。

## 根因

scalpel Makefile 把平台宏放在**目标级变量**里：

```make
CC = gcc
linux: CC += -D__LINUX      # 目标级追加
linux: $(GOAL)
```

GNU make 规定：**变量在命令行定义后，makefile 内（含目标级）的 `+=` 追加被静默忽略**
（make 4.4.1 实测）：

```sh
# 合成实证
printf 'CC = gcc\nCC_OPTS = -Wall\ngoal: CC += -DX\ngoal:\n\t@echo "CC=[$(CC)]"\n' > Makefile
make goal            # CC=[gcc -Wall -DX]     ← 正常
make goal CC=clang   # CC=[clang]             ← -DX 被丢弃，无告警
```

于是 `make linux CC=clang` 编出**没有任何平台定义**的代码：`scalpel.h` 的
`__LINUX` 分支（含 `<libgen.h>`）整体跳过 → `basename()` 无原型 → musl/clang
报上述整型到指针转换错误。

## 方案（配方侧，不动上游）

把平台宏**显式并入命令行 CC**：

```python
comp = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
cc = comp.get("c", "clang") if comp else "clang"
self.run(f'make linux -j1 CC="{cc} -D__LINUX -O2"', cwd=self.source_folder)
```

显式注入是普适安全的：若目标级 `+=` 因未覆盖而生效，也只是重复 `-D`（无害）。

## 判别法

看到 raw Makefile 工程"命令行传 CC 后报隐式声明/整型指针转换"：
1. `make -pn` 或用合成 Makefile 实证目标级 `+=` 是否进值；
2. 再查源码头文件 include 的平台守卫。

## 关联

- 同任务沉淀的另一独立缺陷见 E648（musl realpath NULL → 假 forensic-soundness 告警）。
