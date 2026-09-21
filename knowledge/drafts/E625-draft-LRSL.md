# E625 — 手写 makefile 的 C 包在 OHOS 上的三重确定性陷阱

> 草稿号 E625 ｜ 来源：lrslib 0.73 鸿蒙 PC 适配（上游 release 7.3）
> 状态：draft（未提升）
> 关联：`E011`（HMDFS/临时目录）、`E017`（镜像注入）、`E228`（`.libs` 与真实 ELF）、`E424`

## 一句话

上游用**手写 makefile**（无 configure / 无 CMake）的 C 包，在鸿蒙 PC 上会同时命中三类
「Linux 上全绿、设备上必红」的缺陷：**硬编码 `/tmp` 的 `mkstemp` 模板**、
**装出来的可执行文件没有 `$ORIGIN` RUNPATH**、**CLI 不认 `--version`/`--help`**；
再叠加一条只在**下游**才炸的 `transitive_headers` 缺陷。

## 1. 硬编码 `/tmp` 的 mkstemp：失败之后还 SIGSEGV

lrslib 的两处临时文件模板是字面量：

```c
strcpy(tmpfilename,"/tmp/lrs_stdinXXXXXX");            /* 读 stdin 时的暂存 */
...
strncpy(tmpfilename,"/tmp/lrs_restartXXXXXX",PATH_MAX); /* 64/128bit 溢出重启 */
tmpfd = mkstemp(tmpfilename);
```

设备上 `/tmp` 只读（`Read-only file system`），`mkstemp()` 必然失败。后果分两层：

* **第一层（功能静默丢失）**：`lrs` 的混合算术（64bit → 128bit → GMP）靠把当前问题写进
  重启文件再重跑实现精确恢复。文件建不出来 ⇒ 溢出恢复路径整条丢失。
* **第二层（错误归因被带偏）**：随后 `lrs.c` 的 stage-2 清理调用仍会带着 `P == NULL`
  进 `lrsv2_main`，解引用崩溃，**退出码 139**；而屏幕上只有

```
*Error opening output file /tmp/lrs_restartXXXXXX
*bad input file name
*lrs_setup failed
```

三行全在说"输入文件有问题"，实际根因是临时目录不可写。

实测（修前，`ine/test/` 30 个上游回归输入）：**6/30 崩在 rc=139**
（`cyclic17_8` `in7` `kkd38_6` `kq20_11` `kq20_11a` `truss2`）；修后 30/30 rc=0。

**修法**：模板改为 `$TMPDIR` 优先、`/tmp` 兜底（POSIX 惯例，无平台宏）；并在 stage 0
返回 `-1` 时立即 `exit(1)`，不再进入会解引用的清理调用。

## 2. 交付的可执行文件没有 RUNPATH —— conanrun 下假绿

上游 makefile 的 `install` 把工具放进 `$prefix/bin`、库放进 `$prefix/lib`，但**两条
可执行文件的链接规则完全没有 RUNPATH 挂钩**：

```make
lrs-shared: ${SHLINK} lrs-shared.o
	$(CC) $^ -o $@ -L . -llrs              # 没有 $(LDFLAGS)、没有 $(RUNPATHFLAGS)
```

后果：`bin/lrs` 只能靠 `LD_LIBRARY_PATH` 找到 `liblrs.so.1`。

**这里有一个必须点名的假绿机制**：`test_package` 用 `env="conanrun"` 跑工具时，
conanrun 注入 `LD_LIBRARY_PATH`，**RUNPATH 错成什么样都能装载成功**。
只有 CI 的 **L2 裸 PATH 冒烟**（`bin/<tool> --version`，不带 conanrun）才会以
`rc=127 / Error loading shared library liblrs.so.1` 暴露它。

实测（修前，裸环境）：`bin/lrs cube.ine` → rc=127；`bin/lrsnash` → rc=127 且
`Error relocating ...: lrs_init_gmp: symbol not found`。

**修法**（makefile 两行）：

```make
RUNPATHFLAGS ?= -Wl,-rpath,'$$ORIGIN/../lib'
...
	$(CC) $^ -o $@ -L . -llrs $(RUNPATHFLAGS)
```

* `$$` 是**给 make 的转义**（make 展开成 `$`）；
* 单引号是**给 shell 的**——不加引号，make 拉起的 sh 会把 `$ORIGIN` 当自己的变量展开成空串；
* 判据只看**目标那一行**有没有该变量，不要用"整个文件里出现过 `-rpath` 就跳过"的整文件守卫。

自证：`llvm-readelf -d bin/lrs | grep RUNPATH` → `[$ORIGIN/../lib]`；
`env -u LD_LIBRARY_PATH bin/lrs --version` → rc=0。

## 3. CLI 不认 `--version`/`--help`

`lrs` 把**每一个参数都当输入文件名**，`lrs --version` 等于"打开名为 `--version` 的文件"，
于是 rc≠0（修前甚至 rc=139）。L2 对 `bin/` 下**每个**可执行文件都要求
`--version` 或 `--help` 退出码 0，任一不满足即计入 failed；**全部失败则 L2 直接 FAIL**。
`redund`/`minrep`/`fel` 又是同一个二进制的 argv[0] 别名，所以一次缺陷会让 5 个交付物同时红。

**修法**：在两个 driver 的 `main()` 开头加 `--version`/`--help` 处理并 `return 0`
（`bin/lrs --version` → `lrs (lrslib 7.3)`）。

## 4. 只在消费者侧炸的 `transitive_headers`

`lrslib.h` 通过 `#include ARITH` 选择算术后端，GMP 后端再 `#include "gmp.h"`：

```
lrslib.h → ARITH("lrsgmp.h") → "gmp.h"
```

`gmp.h` 属于**公开头链**，因此 `requires("gmp/6.3.0", transitive_headers=True)` 必需。
漏掉它的表现是：本包 `conan create` 全绿（自己的 `-I` 是自己拼的），
**只有下游 `test_package`/消费者编译红**（`'gmp.h' file not found`）。

## 5. 附带口径（同类手写 makefile 包都会撞）

* 上游 install 规则用 `install -t`，**平台上没有 `install` 命令**
  （`install: inaccessible or not found`）→ 配方用 `copy()` + `os.symlink()` 复刻布局，
  不依赖 `make install`。
* `-L` 该从哪来：`lrsnash-shared` 的链接行是
  `$(CC) ${CFLAGS} ... -L . -llrs -lgmp`，**没有 `-L${LIBDIR}`** —— 依赖库目录只能走
  `CFLAGS` 传进去（clang 在纯编译时会打 `argument unused during compilation` 的噪声，
  属正常）。
* `pkg-config` 无上游 `.pc`，消费者判据用 `cpp_info`（`aggregated_components()`，
  相对路径要用 `package_folder` 补绝对），不要用 `IMPORTED_LOCATION_*` 反推包内路径。
* 自限并发：conan 默认 `tools.build:jobs = os.cpu_count()`，本机 20；
  手写 makefile 没有自己的 job 控制 ⇒ 配方必须显式 `-j{jobs}`。

## 复现命令（设备可直接执行，落 `$TASK_DIR`）

```sh
. "$HOME/tmp/lrslib-0.73/env.sh"
PKG="$PACKAGE_DIR"
BIN=$(conan cache path lrslib/0.73:$(conan list 'lrslib/0.73:*' --format=json 2>/dev/null | python3 -c 'import json,sys;d=json.load(sys.stdin);print(list(list(d.values())[0]["revisions"].values())[0]["packages"].keys().__iter__().__next__())' 2>/dev/null) 2>/dev/null || echo "<pkg>")
# 1. RUNPATH / SONAME
llvm-readelf -d "$BIN/lib/liblrs.so.1.0.0" | grep -E 'SONAME|NEEDED'
llvm-readelf -d "$BIN/bin/lrs" | grep RUNPATH
# 2. 裸环境冒烟（不带 conanrun）
env -u LD_LIBRARY_PATH "$BIN/bin/lrs" --version
env -u LD_LIBRARY_PATH "$BIN/bin/lrsnash" --version
env -u LD_LIBRARY_PATH "$BIN/bin/redund" --version
# 3. 真实计算 + TMPDIR（溢出重启路径）
cd "$TASK_DIR/explore/lrslib-073"
TMPDIR="$TASK_DIR/tmpwork" env -u LD_LIBRARY_PATH "$BIN/bin/lrs" ine/test/cyclic17_8.ine | grep Totals
```
