# 给 Makefile 注入 `-I`/`-L` 只能走环境变量——命令行 `make CFLAGS=` 会顶掉上游 `+=` 默认值；tag 归档无 `.git` 时 `git describe` 条件赋值静默回退，产物自报旧版本号

> DRAFT-lemonbar-1.5-makefile-env-flags-and-git-describe-version-fallback
> （知识库扩展草稿，路径 B）与 lemonbar 1.5 归档同 PR 交付。

lemonbar（LemonBoy/bar，从 stdin 读小型标记语言、渲染成一条 X11 dock 的轻量状态栏）
是个「看着像送分题」的包：纯 C、两个源文件、一个 30 行的 POSIX Makefile、零补丁就能
交叉编译出 aarch64 产物。它真正会咬人的地方全在 **Makefile 的变量优先级**上——
而且两个坑都**不报错**，一个把编译标志静默剥光，另一个把产物版本号静默改错。

上游 `Makefile` 全文（v1.5 tag 归档，逐字）：

```makefile
VERSION = 1.4
GIT_DESC=$(shell test -d .git && git describe --always 2>/dev/null)

ifneq "$(GIT_DESC)" ""
	VERSION=$(GIT_DESC)
endif

CC	?= gcc
CFLAGS += -Wall -std=c99 -Os -DVERSION="\"$(VERSION)\"" -D_GNU_SOURCE
LDFLAGS += -lxcb -lxcb-xinerama -lxcb-randr
...
.c.o:
	${CC} ${CFLAGS} -o $@ -c $<
${EXEC}: ${OBJS}
	${CC} -o ${EXEC} ${OBJS} ${LDFLAGS}
```

---

## 场景一：`make CFLAGS='-I<dep>'` 把上游 `CFLAGS +=` 的默认值全部顶掉

这是 GNU make 的变量优先级，不是 lemonbar 的怪癖：**命令行赋值的变量等价于被
`override`**，Makefile 里对该变量的 `+=` 不再追加。于是

```bash
make CFLAGS='-I/path/to/libxcb/include'
```

得到的编译命令行里 **没有** `-Wall -std=c99 -Os -DVERSION=... -D_GNU_SOURCE`，
只剩一个 `-I`。而 `-DVERSION` 丢失的后果是硬的：

```c
/* lemonbar.c:1412 */
printf ("lemonbar version %s\n", VERSION);
```

`VERSION` 成了未定义标识符 → 编译失败。上游自己的流水线正是这个写法：

```yaml
# upstream .github/workflows/check.yml
- name: Build
  run: CFLAGS='-DWITH_XINERAMA=1' make
- name: Check
  run: ./lemonbar -h || exit 0
```

也就是说上游为了打开 `WITH_XINERAMA`，顺带把自己的 `-DVERSION` 顶掉了；
`|| exit 0` 又让这条流水线无论如何都是绿的。（`WITH_XINERAMA` 本身是另一个坑，
见场景三。）

来自**环境变量**的 `CFLAGS`/`LDFLAGS` 则完全正常——Makefile 的 `+=` 会照常在其上
追加。这就是注入通道的选择依据：

```python
# 正确：环境变量（+= 照常追加）
os.environ["CFLAGS"]  = (os.environ.get("CFLAGS", "")  + " -I<dep>").strip()
os.environ["LDFLAGS"] = (os.environ.get("LDFLAGS", "") + " -L<dep>").strip()
```

```bash
# 错误：命令行变量（+= 被 override 掉，上游默认值全丢）
make CFLAGS='-I<dep>'
```

**判定信号（动手前扫一遍）**：

```bash
grep -nE '^(CFLAGS|CPPFLAGS|LDFLAGS|CXXFLAGS)\s*\+=' Makefile
```

有输出 → 这些变量**只能**经环境变量注入。反向信号：Makefile 里写的是
`override CFLAGS += ...` 或 `CFLAGS := $(CFLAGS) ...` 时，命令行注入不会丢默认值。

> 注意：命令行注入是否「丢默认值」与「丢的值要不要紧」是两件事。丢 `-Os` 只是
> 优化级别变了（无人察觉），丢 `-D_GNU_SOURCE` 是功能差异（一个未声明符号触发
> `#ifdef` 分支），丢 `-DVERSION` 才直接编译失败。**不能因为「编译过了」就认为
> 注入通道选对了。**

---

## 场景二：tag 归档没有 `.git`，`VERSION` 静默回退到硬编码的 1.4

上游用 `git describe` 在构建期取版本，所以 Makefile 里的常量 `VERSION = 1.4`
**自 1.4 之后就再没上调过**——他们本地永远是 `GIT_DESC` 生效、
`VERSION=1.5-3-gabc1234` 之类的串。而打磨适配时拿到的是
`https://github.com/LemonBoy/bar/archive/refs/tags/v1.5.tar.gz` 这种 tag 归档，
解包后是 `bar-1.5/`，**里面没有 `.git`**：

```bash
$ test -d .git && echo yes || echo no
no
$ make -n | grep -m1 -o '\-DVERSION="[^"]*"'
-DVERSION="1.4"          # ← 适配的是 v1.5，产物自报 1.4
```

`test -d .git` 失败 → `GIT_DESC` 为空 → `ifneq` 不成立 → 回落到硬编码常量。
构建成功、链接成功、测试全绿，**唯一异常是版本号是错的**，没有任何报错信号。

修法是最小干预的一种：用**命令行变量**传版本，它的优先级最高，正好盖掉回退值，
而且不必碰上游源码（满足零补丁）：

```bash
make -j1 CC=<ohos-clang> VERSION=1.5
```

```bash
make -n VERSION=1.5 | grep -m1 -o '\-DVERSION="[^"]*"'
-DVERSION="1.5"          # ✅
```

注意这里与场景一并不矛盾：`VERSION` 是**语义参数**（我们要的就是覆盖式传入），
`CFLAGS` 是**通道**（我们要的是追加式注入）。同一个 Makefile 里，前者用命令行、
后者用环境变量，才是各归其位。

**判定信号**：

```bash
grep -nE 'git describe|git rev-parse|GIT_DESC|version\.sh' Makefile
grep -nE '^VERSION\s*=' Makefile          # 伴随一个硬编码回退值
```

两条同时命中 → 任何 tarball/tag 归档构建都会静默回退。

---

## 场景三（附带）：`WITH_XINERAMA` 不在 Makefile 里，README 却宣称支持

```bash
grep -n 'WITH_XINERAMA' Makefile          # 无输出
grep -n 'WITH_XINERAMA' lemonbar.c        # 15: #if WITH_XINERAMA
                                          # 1087: #ifdef WITH_XINERAMA   ← 两处写法还不一致
grep -n -i xinerama README.pod            # 14: "…RandR and Xinerama support…"
grep -n 'xinerama' Makefile               # LDFLAGS += -lxcb-xinerama   ← 无条件链接
```

整个仓库（Makefile / 源码 / 无 config.h）**从不定义该宏**，所以默认 `make` 的产物里
xinerama 代码路径**以及 randr < 1.5 时的回退分支**（`lemonbar.c:1257-1272` 的
`else { ... get_xinerama_monitors(); }`）都被编译掉，而 `-lxcb-xinerama` 那条链接是
纯无用依赖。要启用只能由打包方从命令行 `-DWITH_XINERAMA=1`（上游 CI 的做法）。

**本包的处理**：不打开。这是**特性开关**而非适配所需，打开会改变显示器枚举行为
（randr < 1.5 的 X server 上从「只用第一个 screen」变成「Xinerama 拼屏」），
而我们没有 X server 可以验证任何一条路径。保持与上游默认 `make` 产物一致的编译面，
把发现写进 `manifest.yaml` / `notes.md`，交给后续需要它的人。

---

## 场景四（附带）：`$ORIGIN` 必须带单引号，运行期库不能指望 `LD_LIBRARY_PATH`

`${CC} -o ${EXEC} ${OBJS} ${LDFLAGS}` 这行是由 **shell** 执行的，所以

```bash
LDFLAGS="-Wl,-rpath,$ORIGIN"     # ✗ shell 把 $ORIGIN 展开成空串
LDFLAGS="-Wl,-rpath,'$ORIGIN'"   # ✓ shell 剥掉引号，把 $ORIGIN 原样交给 ld
```

前者**不报错**，只是 rpath 变成了 `-Wl,-rpath,`，被静默忽略。再加
`-Wl,--disable-new-dtags` 强制生成 `DT_RPATH` 而不是 `DT_RUNPATH`（两者 OHOS musl
都认，RPATH 更稳妥）。与之配套的还有一条硬约束：**OHOS musl 加载器忽略
`LD_LIBRARY_PATH`**，所以运行期 `.so` 必须随二进制装入 `bin/`，让 `$ORIGIN` 有东西
可解析（xeyes / myman 同款做法）：

```python
RUNTIME_LIBS = (("libxcb", "libxcb*.so*"),
                ("libxau", "libXau*.so*"),
                ("libxdmcp", "libXdmcp*.so*"))
```

---

## 一个反直觉的副产品：无 X 的失败路径本身就是链接完整性探针

lemonbar 的 `main()` 把 `xconn()` 放在 `getopt()` **之前**：

```c
// lemonbar.c:1406-1412
    // Connect to the Xserver and initialize scr
    xconn();
    while ((ch = getopt(argc, argv, "hg:o:bdf:a:pu:B:F:U:n:")) != -1) {
        switch (ch) {
            case 'h':
                printf ("lemonbar version %s\n", VERSION);   // ← 无 X 时不可达
```

而

```c
// lemonbar.c:1205-1213
xconn (void) {
    c = xcb_connect (NULL, NULL);
    if (xcb_connection_has_error(c)) {
        fprintf(stderr, "Couldn't connect to X\n");
        exit(EXIT_FAILURE);
    }
```

CI 构建机**没有 X server**，所以 `-h`/版本输出根本不可达，唯一可观测的行为是
这句话 + 退出码 1。这看着像「测不了任何东西」，实际上是一条相当有信息量的断言：

> 进程能打印 `Couldn't connect to X` ⟹ `main()` 已经跑起来、所有 `DT_NEEDED`
> 都解析成功了（`libxcb.so.1` + `libxcb-randr.so.0` + `libxcb-xinerama.so.0` +
> `libXau.so.6` + `libXdmcp.so.6`，全部经 `$ORIGIN` rpath 从 `bin/` 取到）。
> 只要漏一个，OHOS 加载器会在 `main()` 之前就报 `cannot open shared object`，
> 拿到的是**另一种 stderr**。

于是 test_package 的断言可以写得又诚实又有牙：

```sh
# 退出码必须是 1（EXIT_FAILURE），不是 127/126/加载器错误
ok - exits 1 when no X display is available
ok - reports "Couldn't connect to X" on stderr
ok - no dynamic loader errors (bundled libxcb chain resolved)
ok - -h exits 1 with the X error instead of printing help   # 记录上游顺序，未来变了能被发现
ok - runtime libraries are bundled next to the binary
```

8 条断言全绿（`test_package/test_lemonbar.sh`）。**上游测试数是 0**——不是「没跑」
而是真的没有：tarball 只有 7 个文件，Makefile 的 target 只有
`all/doc/debug/clean/install/uninstall/.c.o`，`check.yml` 只是个构建流水线
（末行 `|| exit 0` 无条件成功）。审计逐项列在 `test_package/MANIFEST.yml`，
按 rule4 的口径如实声明 0，不虚报也不含糊。

---

## 复现清单

```bash
# 1) 通道判据
grep -nE '^(CFLAGS|CPPFLAGS|LDFLAGS)\s*\+=' Makefile        # 有输出 → 必须走环境变量
grep -nE 'git describe|GIT_DESC' Makefile                    # 有输出 → tag 归档会回退
# 2) 真值判据（dry-run 看真实编译行，别只看构建是否成功）
make -n VERSION=1.5 | grep -m1 -- '-DVERSION'                # 期望 -DVERSION="1.5"
make -n CFLAGS='-DXX' | grep -c -- '-DVERSION'               # 期望 0 → 被 override 顶掉
# 3) 运行期判据
readelf -d bin/lemonbar | grep -E 'RPATH|RUNPATH'            # 期望 $ORIGIN，非绝对路径
```
