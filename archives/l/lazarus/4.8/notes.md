# lazarus 4.8 适配笔记（HarmonyOS PC / aarch64）

## 结论

- **交付范围**：`make lazbuild` 目标 —— 命令行构建工具 `lazbuild` + `nogui` LCL 组件库 + 组件单元 + `lazres`/`lrstolfm`/`updatepofiles` 工具。
- **不交付** GTK/Qt 的 RAD IDE：OHOS PC 无 X server（GTK 无法开显示），且 FPC 的 GTK2 绑定请求 glibc 时代 soname（`-lglib-2.0.0`、`-lgdk-x11-2.0`、`-lgdkglext-x11-1.0`…），OHOS GTK2 栈不提供，`gtk2/2.24.33` 的传递闭包在制品仓也不完整；`LCL_PLATFORM=nogui` 又不被 IDE 组件包支持（缺 `include/nogui/uses.inc`）。
- **目标**：aarch64-linux（FPC 3.2.2 无 `ohos` 目标）。LCL 使用 `dlopen`，链接 OHOS musl `libc.so`，故产物为**动态可执行文件**（FPC RTL 部分仍为静态）。
- **依赖**：仅 `tool_requires(fpc/3.2.2)`；无其它第三方 conan 依赖。

## 三个必须的修复

### 1. FPC 启动器 `-Fu` 顺序遮蔽 LCL 单元

`fpc` 包的启动器把**所有**包 unit 目录以命令行 `-Fu` 传入，且排在调用方 `-Fu` 之前；FPC 取**首个匹配**目录，于是 FPC 的 `fv` 包（`menus.ppu`、`dialogs.ppu`）遮蔽 LCL 的同名单元，报：

~~~
Recompiling Controls, checksum changed for .../units/aarch64-linux/fv/menus.ppu
Fatal: (10022) Can't find unit Controls used by WSProc
~~~

配方生成 wrapper，把 FPC 包 unit 目录追加到调用方 `-Fu` **之后**（并剔除 `fv`/`jni`），等价于系统 FPC 安装（其 unit 目录来自 `fpc.cfg`，命令行走在其前）。

### 2. OHOS sysroot：`-ldl`/`-lc`、宿主 gcc 目录

FPC 的 Linux RTL 链接 `-ldl`/`-lpthread`/`-lc`；OHOS sysroot 里 `libdl.a`/`libpthread.a` 是 **8 字节空占位**，真正符号在 musl `libc.so`。wrapper 追加 `-Fl<sysroot>/usr/lib/aarch64-linux-ohos`。

同时 lazarus 的 Makefile 用 `gcc -print-libgcc-file-name` 得到**宿主** x86_64 gcc 目录并 `-Fl`，其 `crtbegin.o` 与 FPC 的 aarch64 `cprt0.o` 不兼容：

~~~
ld.lld: error: /usr/lib/gcc/x86_64-linux-gnu/13/crtbegin.o is incompatible with .../rtl/cprt0.o
~~~

故 `make` 显式传 `GCCLIBDIR=`（另见 `ld.lld: error: unable to find library -ldl`）。

### 3. glibc 启动 shim + ELF 解释器

FPC 的 `cprt0.o` 引用 glibc 专有的 `__libc_csu_init`/`__libc_csu_fini`，musl 不提供：

~~~
ld.lld: error: undefined symbol: __libc_csu_init
~~~

配方用 OHOS clang 汇编一个空实现 shim 并 `-k<shim.o>` 链入；FPC 仍写入默认解释器 `/lib/ld-linux-aarch64.so.1`，配方在 `package()` 中把 `.interp` 就地改写为 `/lib/ld-musl-aarch64.so.1`（OHOS）。

## 打包与可重定位

- 无法用 `make install`：该目标要求 `lazarus`/`startlazarus` 同时存在，而本方案只构建 `lazbuild`。
- 配方把整个构建树复制到 `share/lazarus/`，并在 `bin/` 生成可重定位 shell 启动器：
  - `bin/lazbuild` → `share/lazarus/lazbuild --lazarusdir=share/lazarus`
  - `bin/lazres|lrstolfm|updatepofiles` → `share/lazarus/tools/*`
- 启动器按自身路径推导包根，conan 缓存路径变化后仍可用。

## 验证

- 本地 aarch64 构建（qemu-binfmt 运行打包 fpc）：`make lazbuild` 成功；`lazbuild --version` = `4.8`、`--help` 正常。
- 交叉构建 profile：WSL `ohos-aarch64-wsl`；CI profile：`ci/conan/profiles/ohos-aarch64`（原生 aarch64）。
- test_package：断言 `lazbuild --version/-v` = 4.8、`--help` 退出 0、LCL nogui 单元与工具齐备。

## 上游测试（testsuite）

- 上游入口：`test/runtests.lpi`（fpcunit console runner），`./runtests --list` 注册 **406** 个用例 / 353 个 suite。
- 为跑通做了 **3 处测试专用补丁**（不改上游功能源码；在 PR 的「上游测试用例修改说明」逐条申报）：
  1. `test/runtests.lpr`：uses 去掉 `lazmouseandkeyinput`（该包在 Linux 拉 `-lXtst`/X11，无 X server 必失败）；
  2. `test/runtests.lpi`：`RequiredPackages` 去掉 `lazmouseandkeyinput`；
  3. `test/testunits.pas`：去掉 `TestListView`（依赖 `MouseAndKeyInput`）。
- 实跑（本机 aarch64 交付物 + qemu-binfmt，nogui）：14 个单元测试 suite，**48 项：通过 41 / 失败 3 / 错误 4（85.4%）**。
  - 6 项为 nogui widgetset 缺真实控件（`TTestPen` "Creating of APen failed" ×2、`TTestPreferredSize` EAccessViolation ×4）；
  - 1 项为代码页往返差异（`TTestLConvEncoding.Test_CP_UTF8_CP`，cp852 字符 #128 回转 #199）；
  - 未跑的 358 项为 `Bugs`(40)/`Projects`(168)/`Packages`(149) 三组「编译并运行独立工程」套件：需要完整 GUI widgetset + X server，且 qemu 下逐个 lazbuild 数小时（`--all` 在第一个 bug 工程即停滞）。
- 证据：`tasks/lazarus-4.8-2026-09-25/logs/090-upstream-runtests-list.log`（406/353 清单）、`091-upstream-runtests-build.log`（`runtests` 编译）、`092-upstream-runtests-unit-subset.log`（逐 suite 明细）。

## 与 fpc 的关系

- `tool_requires(fpc/3.2.2)`；lazarus 的 Makefile 要求 `FPCDIR/rtl` 存在，由 fpc 包交付的上游 `rtl/` 源码子树满足。
- 本适配发现并绕过了 fpc 启动器 `-Fu` 顺序的问题；未修改 fpc 包本身（另有独立 PR）。
