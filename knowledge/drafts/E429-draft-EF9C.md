# E429 — Makefile 用 `CFLAGS ?=` 时被环境 CFLAGS 顶掉，vendored include 目录丢失

> 草稿（DRAFT，contributor EF9C）。与同目录 `E429-draft-EF9C.kv` 成对。
> 来源：libpktriggercord/0.85.1-20221221181244 探索编译，2026-09-17。

## 错误特征

上游 Makefile 里写着

```make
JSONDIR=src/external/js0n
CFLAGS ?= -O3 -g -Wall -I$(JSONDIR)
LDFLAGS ?= -lm
```

在把 `CFLAGS` 导出到环境（设备 profile、conan `MakeToolchain`、worker shell）的机器上，
`make` 报的是**找不到上游自己的内嵌头文件**：

```text
clang -fPIC -O2 -DPKTDATADIR=\"/usr/local/share/pktriggercord\" -fPIC -c pslr_model.c -o pslr_model.o
pslr_model.c:45:10: fatal error: 'js0n.h' file not found
    #include "js0n.h"
make: *** [Makefile:129: pslr_model.o] Error 1
```

注意编译回显里只有 `-fPIC -O2`（= 环境的值），**上游默认值整条不见了**，
`-Isrc/external/js0n`、`-O3`、`-Wall` 一起消失。同理 `LDFLAGS ?= -lm` 也会被
环境的 `LDFLAGS=-L/home/xx/usr/local/lib` 顶掉（表现为 `-lm` 丢失，musl 下因
libm 并入 libc 而不会暴露，换 glibc 就会报 undefined `lgamma` 一类符号）。

## 触发条件

- 构建系统：裸 Makefile（无 configure / CMake / meson），且变量以 `?=` 定义默认值
- 阶段：`make` 编译或链接
- 环境：任何预先导出 `CFLAGS` / `CXXFLAGS` / `LDFLAGS` 的场景
  （OHOS worker 常见：profile `[buildenv]`、`MakeToolchain`、`~/usr/local` 注入）

## 根因分析

GNU make 会把环境变量作为变量导入，`?=`（set-if-undefined）在这种情况**完全不执行右侧赋值**，
而不是"追加"。因此上游默认值（往往携带 `-I` 到 vendored 源码目录、必要的 `-D`、`-lm`）
被环境值整体替换。这不是 OHOS 特有问题，但在鸿蒙 PC worker 上必然命中，因为工具链
环境通常会导出 `CFLAGS=-fPIC -O2`。

## 解决方案

### 推荐方案（rec_priority 1）

用 **make 命令行变量**显式传入完整值——命令行变量优先级高于环境，可完全覆盖：

```bash
make cli CFLAGS="-O3 -g -Wall -fPIC -Isrc/external/js0n" LDFLAGS="-lm" -j1
```

配方里等价写法（编译器取自 Conan conf，符合 R33，不裸用 `${CC}`）：

```python
cflags = "-O3 -g -Wall -fPIC -Isrc/external/js0n"   # 保住上游默认值
self._run('make cli CC="%s" CFLAGS="%s" LDFLAGS="-lm" -j1' % (cc, cflags), cwd=src)
```

### 回退方案（priority 2）

把上游 `CFLAGS ?=` 改成 `CFLAGS +=`（保留默认值再追加），通过 `patches/` 交付。
比命令行方案更可移植（`make`、`make install` 等所有入口都受益），代价是要维护补丁。

### 禁止做法

- ❌ 在配方里 `unset CFLAGS` / `CFLAGS=""`：只是把问题挪走，`LDFLAGS`、
  `PKG_CONFIG_PATH` 等仍会踩同一 `?=` 语义，换 worker 就复发。
- ❌ 只加 `-I` 到 `CPATH`：上游编译回显仍缺 `-O3/-Wall`，且暴露不出"默认值被顶掉"
  这一真实缺陷，后续同类包会继续踩。

## 验证

```bash
$ grep -n 'CFLAGS ?=\|LDFLAGS ?=' Makefile
5:CFLAGS ?= -O3 -g -Wall -I$(JSONDIR)
7:LDFLAGS ?= -lm
$ echo "env CFLAGS=[$CFLAGS]"          # 非空即命中本模式
env CFLAGS=[-fPIC -O2]
$ make cli CFLAGS="$CFLAGS -O3 -Wall -Isrc/external/js0n"   # 修复后
exit=0
```

预扫描建议（`prescan_pattern: CFLAGS\s*\?=\s*.*-I\$\(`）：命中即提示"该上游 Makefile
的默认 CFLAGS 携带 include 目录，环境覆盖会导致头文件找不到"。
