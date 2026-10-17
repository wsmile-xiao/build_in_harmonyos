# DRAFT: Conan 2.29 — `tc.generate()` 放在 `build()` 会让工具链环境静默失效，configure 回落到宿主 gcc

- **package**: vtgrab/0.1.8
- **context**: Conan 2.29.1 + `AutotoolsToolchain`，小型 autotools C 项目，宿主装有 gcc 与 ncurses-dev
- **verdict**: works — 工具链生成移到 `generate()`，并强制 in-tree 构建

## error_signature

按尝试顺序会看到这几种报错，它们是同一个根因的不同外衣：

```
AttributeError: 'AutotoolsToolchain' object has no attribute 'configure'
AssertionError: env argument to ConanFile.run() should be a list
AttributeError: 'str' object has no attribute '_values'
/bin/sh: 1: ./configure: not found
```

把它们都"修掉"之后，真正的危险才出现 —— `conan create` 返回 0、包也打出来了，
但生成的 Makefile 里是：

```make
CC = gcc
CPPFLAGS =
LDFLAGS =
LIBS =
```

`CC = gcc` 就是中招的确证。

## root_cause

1. Conan 2.29 的 `Environment` 只剩 `vars()`（返回 `EnvVars`），没有
   `save_script()` / `define()`；`AutotoolsToolchain` 也**没有** `configure()` 方法，
   `configure_args` 只是普通属性。在 `build()` 里调 `tc.generate(env=...)`，
   `conanautotoolstoolchain.sh` 会落进 generators 目录，却不会被接进聚合后的
   `conanbuild.sh`；于是 `self.run(..., env="conanbuild")` 拿不到任何工具链变量。
2. autoconf 的 `configure` 对 `CC` 缺失毫无戒心 —— 它退回宿主默认编译器继续跑。
   宿主有 gcc + ncurses-dev 时，`#include <curses.h>` 甚至能过，编译链接一路"成功"，
   唯独链接 ncurses 时因为没有 `-lncursesw` 才暴露，而且是以一种看起来像配方 bug 的形式。
3. 同源的第二个坑：`basic_layout()` 默认 `src_folder="."` 而
   `build_folder="build/<build_type>"`，Conan 会把源码**复制**进 build 目录；
   在 `build()` 里 `self.run("./configure")` 的 cwd 里没有 `configure`。
   顺带一提，`AutotoolsToolchain.__init__` 会算 `_is_cross_building` 并准备
   `--host=<triplet>`，而 autoconf 2.13 的 configure 没有 `AC_CANONICAL_HOST`，
   这些 triplet 参数对它毫无意义，只能自己传 `--prefix`。

## rec_approach

- 把工具链生成放进配方的 `generate()` 方法。那一步 generators 目录与 conf 文件
  都已就绪，脚本才会被接进 `conanbuild.sh`；`build()` 里一律用 `env="conanbuild"`。
- in-tree 构建，显式消除源码复制带来的路径歧义：

  ```python
  def layout(self):
      basic_layout(self, src_folder=".", build_folder=".")
  ```

- 依赖的头文件/库路径不要依赖 CFLAGS 通道（见下面的附加陷阱 2）。
- **验收动作**：每次交叉编译配方都回读生成的 Makefile 确认 `CC` 不是宿主编译器：

  ```bash
  grep -nE '^CC = |^CPPFLAGS = |^LIBS = ' <build_folder>/Makefile
  ```

  或直接在 `package()` 里断言产物架构 —— vtgrab 的
  `test_package/ohos_binary_check.py` 就是这种自检（`e_machine == 183` +
  `PT_INTERP == /lib/ld-linux-aarch64.so.1`）。

## 附加陷阱

### 1. 改了 recipe 后 `conan create` 会复用旧二进制

recipe revision 变了但 `package_id` 没变（vtgrab 是纯 C 应用，package_id 只看
settings/options），Conan 直接复用缓存产物 —— 断言全绿，验的却是上一版代码。
`--build=vtgrab` 在 2.29 里不生效，可靠做法是先删：

```bash
conan remove "vtgrab/0.1.8:*" -c
conan create archives/v/vtgrab/0.1.8 -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing
```

### 2. 上游老 Makefile 写死 CFLAGS

`Makefile.in: CFLAGS = -D_GNU_SOURCE -Wall -W -O2` 会覆盖工具链注入的 CFLAGS
（Makefile 变量优先于环境变量）。于是：

- 依赖头文件路径放 `CPPFLAGS`（独立变量，不被覆盖）；
- 库路径放 `LDFLAGS`（独立变量）；
- `build_type` 的优化/调试标志用 make 命令行变量覆盖（命令行赋值优先级最高）：

  ```python
  self._build_cflags = " ".join(["-D_GNU_SOURCE", "-Wall", "-W"] + tc.cflags)
  self.run("make -j1 CFLAGS='%s'" % self._build_cflags, env="conanbuild")
  ```

### 3. 宿主 musl loader 缺 `__fd_chk`

OHOS 的 `sys/select.h` 把 `FD_SET/FD_CLR` 加固成调用 `__fd_chk`；OHOS 平台 libc
（DevEco NDK sysroot 的 `libc.so`，约 72KB）导出该符号，本地 binfmt/qemu 用的通用
musl loader 没有。于是任何用到 `select()` 的 OHOS 动态产物在本地都报：

```
Error relocating ./prog: __fd_chk: symbol not found
```

这是**本地 loader 差异，不是配方缺陷**（真机 CI 直接执行）。反证方式：编一个
`void __fd_chk(int fd){(void)fd;}` 的 aarch64 共享库，用
`QEMU_SET_ENV=LD_PRELOAD=…` 只注入 guest（不污染宿主进程）后即可真跑。

## related

- 同仓已有条目记录了 `__fd_chk` 的另一面（宿主侧 fortify 依赖导致链接失败，
  `archives/g/gsoap/2.8.142`、`archives/y/yosys/0.66`）；本条补的是"产物能编出来但
  只能在特定 loader 下装载"这一半。
- 运行时范围要如实申报：vtgrab 的抓屏能力依赖 Linux 虚拟文本控制台
  （`/dev/vcsaN` + `VT_GETSTATE`/`KDGETMODE`），OHOS 没有，详见该包 notes.md。
