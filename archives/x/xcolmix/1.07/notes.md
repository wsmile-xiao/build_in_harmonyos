# notes.md — xcolmix 1.07 适配 HarmonyOS PC（OHOS aarch64）

> 本文件记录本轮适配的实测结论与取舍依据。所有"实测"数字均来自本机 WSL
> （profile `ohos-aarch64-wsl`）与 CI 同源门禁 `ci/conan/build_and_test.sh` 的真实输出。

## 1. 上游与源码来源

| 项 | 值 |
|---|---|
| 软件 | xcolmix — X11 RGB 混色器（XForms 前端） |
| 上游版本 | 1.07（`src/version.h`：`#define VER "1.07"`） |
| 作者 / 年份 | Karel Kubat (ICCE, Rijksuniversiteit Groningen)，1996 |
| 上游声明的许可证 | GPL-2.0-or-later + 允许链接 XForms 的第 3 条例外（`xcolmix.README`、`COPYING`） |
| 上游 ChangeLog 末条 | `1999-06-11 … * Version 1.07 released.` |
| 官方分发点 | `ftp.icce.rug.nl:/pub/unix/xcolmix-X.YY.tar.gz`（README 自述） |

**官方分发点已不可达**（本轮实测）：

```
$ curl -sI http://ftp.icce.rug.nl/pub/unix/xcolmix-1.07.tar.gz   → 无响应
$ curl -sI https://www.icce.rug.nl/                             → 无响应
$ curl -sIL https://invisible-island.net/archives/xcolmix/      → HTTP 404
$ curl -sIL https://invisible-island.net/datafiles/release/xcolmix.tar.gz → HTTP 404
```

xcolmix 是 1996 年的 X11 工具，其后由 xterm 390 一侧长期沿用（Thomas Dickey
站点只随 xterm 分发，不托管 xcolmix 的历史归档）。因此 `conandata.yml` 取
**Debian 官方镜像的 `.orig` 归档** —— 按 Debian 的 quilt 约定，`.orig` 就是未经
改动的上游原始发布件（`.debian.tar.xz` 才是 Debian 自己的补丁），且其
sha256 由 GPG 签名的 `.dsc` 声明，与本地实测一致：

```
1955698b1d9e62d9af8eef8f544e4509025785c49bef914296fa90987780ef17  16460  xcolmix_1.07.orig.tar.gz
```

tarball 共 21 个成员，`strip_root` 后为 `xcolmix-1.07/{COPYING,GPL,ChangeLog,
xcolmix.README,xcolmix.lsm,src/}`，`src/` 内是 7 个 `.c` + 3 个 `.h` + 1 个手写
`Makefile` + `xcolmix.1` man page + `design.fd`。

## 2. 构建系统：纯手写 Makefile，且硬编码了编译/链接标志

`src/Makefile` 没有 configure、没有 autotools/meson/cmake 胶水。关键片段：

```make
STDCFLAGS = -c -O2 -Wall $(XFINCDIR)
STDLFLAGS = -s -L/usr/X11R6/lib

final:
	make xcolmix CFLAGS="$(STDCFLAGS)" LFLAGS="$(STDLFLAGS)"

xcolmix: $(OBJ)
	$(CC) -o xcolmix.new $(OBJ) $(XFLIBDIR) -lforms -lX11 -lm $(LFLAGS)
```

三个由此产生的决定：

1. **依赖搜索路径不能走 `CFLAGS`/`LDFLAGS`**：`final` 在子 make 的**命令行**上
   硬写了 `CFLAGS=` 与 `LFLAGS=`，命令行赋值优先于 conan 注入的环境变量。
   解法不是绕开 `final`（那会丢掉上游的构建语义），而是使用 Makefile 注释里
   自己写明的两个旋钮：

   > "If you have installed XForms as the Makefile of the package does, you won't
   > have any problems compiling all. **Otherwise, set XFLIBDIR to "-L..." and
   > XFLIBINC to "-I..."**"

   配方据此传 `XFINCDIR=` / `XFLIBDIR=`，`final` 原样执行。

2. **树内构建**：`OBJ` 按裸文件名列（`xcolmix.o callbacks.o …`），没有 VPATH
   规则，也没有 `builddir` 概念，因此 `folders.source="."`（`strip_root` 后
   上游顶层即 source 根）、`folders.build="src"`。generators 目录放在
   `conan-generators/`，避免生成物落进源码树布局。

3. **不用 `make install`**：它依赖 `install -s` 与 `$(prefix)/man/man1` 布局。
   `package()` 显式落 `bin/xcolmix` + `share/man/man1/xcolmix.1` +
   `licenses/{COPYING,GPL}`，并断言包根只有这三项、包内无任何 `.so`
   （application 包不得携带共享库，R26）。

### 2.1 `STDLFLAGS` 是上游的拼写错误（不要"修"它）

`final` 用的是 `LFLAGS="$(STDLFLAGS)"`（应为 `STDLFLAGS`），所以链接行恒定带一个
`-L/usr/X11R6/lib`。该目录在 OHOS 不存在，链接器忽略不存在的 `-L`，实测无警告、
无影响。**刻意不修改**：改它属于与任务无关的上游改动。

### 2.2 编译期的宏从哪来（实测确认）

`AutotoolsDeps` 把依赖的 `-I/-D` 写进构建环境的 `CPPFLAGS`，而 make 的内建
`.c.o` 规则是 `$(CC) $(CFLAGS) $(CPPFLAGS) -c`，所以这些宏确实进了编译行。
实测编译行（节选）：

```
/opt/lpk-fixed/clang -c -O2 -Wall -I<libforms>/include … -DNDEBUG … \
    -D_DEFAULT_SOURCE -D_BSD_SOURCE -DHAS_STICKY_DIR_BIT -DHAS_FCHOWN  -c -o usage.o usage.c
```

但为了可审阅，配方仍**显式**把依赖 include/lib 目录经 `XFINCDIR`/`XFLIBDIR`
传进去，不依赖 make 内建规则的隐式行为。

## 3. 唯一一处源码改动：XForms 公共头的 include 路径

上游（及 Debian 的 1.07 打包）写 `#include <X11/forms.h>`——X11R6 时代的安装
布局。上游 ChangeLog 的 1.07 条目正好记录了这个动作：

```
* Makefile did not build properly
    design.c and xcolmix.h now have #include <X11/forms.h>
```

而 `libforms/1.2.4` 这个 conan 包把**构建生成**的公共头装成
`include/forms.h`（包内没有 `include/X11/` 目录）：

```
libforms/1.2.4/Release/armv8/include/forms.h
libforms/1.2.4/Release/armv8/include/flimage.h
```

于是 `patches/0001-xforms-public-header-include-path.patch` 把两个翻译单元
（`src/xcolmix.h`、`src/design.c`）的这条 include 改成 `<forms.h>`。
**纯 include 路径适配，不含任何平台宏**（R8），找到的是同一个头文件，
它内部仍然经 libforms 自己的 include 链到达 `<X11/Xlib.h>`。

## 4. 依赖（W0：适配前先验，全部已发布）

`conan download "<ref>" -r=ohpcd`（R35：不使用 `conan list` 判断）逐个核对，
并用真实图解析确认二进制命中缓存而非 `--build=missing` 回编：

| 依赖 | 用途 | 制品仓状态 |
|---|---|---|
| `libforms/1.2.4` | XForms 库（`forms.h` + `libforms.so.2`） | recipe + OHOS armv8 binary 均已发布 |
| `libx11/6.4.0`（force） | 上游链接行显式 `-lX11`；`X11/Xlib.h` | 同上 |
| `xorgproto/2025.1` | X11 协议头 | 同上 |
| `libxpm/3.5.17`（run） | `libforms.so.2` 的 DT_NEEDED 闭包 | 同上 |
| `libxcb/1.16`（run） | `libX11.so.6` / `libXpm.so.4` 的 DT_NEEDED 闭包 | 同上 |
| `libxau/1.0.11`（run） | `libxcb.so.1` 的 DT_NEEDED 闭包 | 同上 |
| `libxdmcp/1.1.5`（run） | `libxcb.so.1` 的 DT_NEEDED 闭包 | 同上 |

`libjpeg/10` 只以静态归档 `libjpeg.a` 出现在 `libforms` 的 cpp_info 里，
不进入运行期闭包，故不声明为 run 依赖。

**`-lX11` 不能省**：链接行是 `$(CC) -o xcolmix.new $(OBJ) $(XFLIBDIR) -lforms -lX11 -lm`，
`libforms` 只在自己的 `cpp_info.requires` 里带 `libx11::libx11`，不直接提供
`-lX11` 的搜索目录。

实测 `conan create` 解析出的依赖图（9 个包全部 `- Cache`，即用制品仓二进制）：

```
libforms/1.2.4#4646438b…  libjpeg/10#b07f9629…  libx11/6.4.0#63e25e48…
libxau/1.0.11#e70832a1…  libxcb/1.16#eb6f913a…  libxdmcp/1.1.5#8aaf268a…
libxpm/3.5.17#e08a8195…  xorgproto/2025.1#f5274e33…  xtrans/1.6.0#664ea4b0…
```

## 5. 产物的动态链接契约（实测）

```
$ readelf -d <package>/bin/xcolmix | grep -E 'NEEDED|FLAGS_1'
 (NEEDED)  Shared library: [libforms.so.2]
 (NEEDED)  Shared library: [libX11.so.6]
 (NEEDED)  Shared library: [libc.so]
 (FLAGS_1) Flags: PIE
$ file <package>/bin/xcolmix
ELF 64-bit LSB pie executable, ARM aarch64, … interpreter /lib/ld-linux-aarch64.so.1
```

`nm -D --undefined-only` 显示 **43 个 `fl_*` 未定义符号**（`fl_initialize`、
`fl_do_forms`、`fl_show_form`、`fl_add_browser` …）——产物是对已适配 XForms 栈的
真实动态绑定，不是内联或空实现。

## 6. 图形路径为什么不能作为 CI 断言（实测三条“不能测”的路径）

| 命令行 | 实测结果 | 结论 |
|---|---|---|
| `xcolmix`（无参数） | `rc=124`（`timeout` 命中）；有可用 `$DISPLAY` 时 `fl_do_forms()` 阻塞，无 display 时 `initforms()` 段错误（`SIGSEGV`） | **不可断言**：阻塞或崩，且与 worker 是否有 display 有关 |
| `xcolmix /可读文件` | 同上（接受参数后继续建表单） | **不可断言** |
| `xcolmix --version` / `-help` | `rc=1` + usage 横幅 | 与非法参数同一条路径，无独立信息；CI L2 冒烟因此为 `warn`（非阻塞） |

`src/xcolmix.c` 的 `main()` 结构决定了可断言的分支只有三条（都在显示窗口之前）：

```c
fl_initialize (&argc, argv, "XColmix", 0, 0);   /* XForms；无 display 时返回 NULL */
if (argc > 2)              usage ();
else if (argc == 2) { if (access (argv [1], R_OK)) usage (); rgbfile = argv [1]; }
initforms ();  fl_show_form (...);  fl_do_forms ();
```

其中第 3 条测试用 `-display 127.0.0.1:99` 把 display 强制到**关闭的回环端口**，
使 `fl_initialize()` 的 `XOpenDisplay` 必然失败 —— 这样"XForms 代码确实在进程内
执行过"就成为一条与 worker 环境无关的确定性断言：

```
In fl_initialize() [flresource.c:995]: …/bin/xcolmix: Can't open display 127.0.0.1:99
```

### 6.1 上游代码里的两处编译告警（不改）

- `xcolmix.c:54` `void main (int argc, char **argv)` → `-Wmain-return-type`。
  XForms 1.2.4 的 `fl_initialize` 仍返回 `Display *`，调用点传 4 个实参在
  OHOS/clang 15 上实测正常返回（无 display 时打印诊断后返回 NULL），
  改 `int main` 属与任务无关的上游改动。
- `callbacks.c:61` / `usage.c:57` 隐式声明 `exit()` → `-Wimplicit-function-declaration`。
  实测行为正确（`usage()` 退出码 1），补 `<stdlib.h>` 同样属无关改动。

两条都只是 warning，不影响 `-Wall` 下构建成功。

## 7. 测试证据（20 项断言，全部实测通过）

`test_package` 分两路，都打在**打包后的产物**上：

1. **`test_package/conanfile.py :: test_elf_contract`（11 项）** —— 用 `struct`
   直接解析 `<package>/bin/xcolmix` 的 ELF64 映像：magic、ELFCLASS64、
   `e_machine==EM_AARCH64(183)`、`e_type==ET_DYN`、`PT_INTERP` 为绝对路径、
   `DT_NEEDED` 含 `libforms.so.2`/`libX11.so.6`/`libc.so`、`DT_NEEDED` 无绝对或
   `../` 路径、`DT_FLAGS_1` 含 `DF_1_PIE`。不依赖 `readelf`/`llvm-readelf`，
   交叉构建宿主与真机 worker 行为一致。
2. **`test_package/test_xcolmix.sh`（9 项）** —— 真实执行打包二进制的三条命令行
   （见 §6），断言退出码与 `src/usage.c` 打印的横幅。横幅里的 `V1.07` 直接来自
   `src/version.h`，因此这一条同时是"版本正确"与"产物确由本包源码构建"的断言。

实测输出（`conan create` 的 test 阶段）：

```
xcolmix/1.07 (test package): XCOLMIX_ELF_INTERP=/lib/ld-linux-aarch64.so.1
xcolmix/1.07 (test package): XCOLMIX_DT_NEEDED=libX11.so.6,libc.so,libforms.so.2
xcolmix/1.07 (test package): XCOLMIX_ELF_ASSERTIONS=11
xcolmix/1.07 (test package): runtime LD_PRELOAD entries=32
…
xcolmix runtime assertions: 9/9
HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,…,"discovered":9,"passedCount":9}
CONAN_CREATE_EXIT=0
```

### 7.1 L1e 反向破坏（证明测试非空壳）

见 `reports/test-report.md` 的 L1e 一节：把包的 `bin/` 移走后重跑
`conan test`，测试**必须失败**（ELF 契约第 1 项即 `packaged executable is missing`）。

## 8. 运行期寻库

`libforms.so.2` 的 DT_NEEDED 闭包很大（`libXpm.so.4` + `libX11-xcb.so.1` +
`libX11.so.6` + 24 个 `libxcb-*.so.0` 扩展 + `libxcb.so.1` + `libXau.so.6` +
`libXdmcp.so.6`，实测 31 条）。两条保障：

1. 配方把全部共享库依赖声明为 `run=True`，`VirtualRunEnv` 把各自 libdir 注入
   `LD_LIBRARY_PATH`；
2. `test_package` 另外把各依赖包 libdir 下的**实体**（非符号链接）`.so` 绝对路径
   拼成 `LD_PRELOAD` 传给脚本，与 xev 1.2.7 同款（应对鸿蒙 loader 的
   `stale_runtime_library`）。脚本对 `LD_PRELOAD` 是**追加**而非覆盖，
   调用方已导出的值不丢。

## 9. 本地门禁与真机的已知差异（如实记录）

### 9.1 本机 qemu guest libc 缺 `__fd_chk` / `arc4random`（环境类，非配方缺陷）

本机执行 aarch64/OHOS 产物靠 `binfmt_misc` + `/opt/ohos-guest/lib/ld-linux-aarch64.so.1`
（stock musl 1.2.6）。首次直接执行时：

```
Error relocating …/libforms.so.2: __fd_chk: symbol not found
Error relocating …/libX11.so.6: __fd_chk: symbol not found
Error relocating …/libXdmcp.so.6: arc4random_buf: symbol not found
rc=127
```

对照 DevEco SDK 的 OHOS libc（`…/native/sysroot/usr/lib/aarch64-linux-ohos/libc.so`）
`nm -D` 可见它**确实导出** `__fd_chk` 与 `arc4random_buf`（`__fd_chk` 是 OHOS
`sys/select.h` 里 `FD_SET` 的边界检查辅助函数，全部 `__*_chk` 别名到同一个
`__chk_fail` 地址）。也就是说这是**本地 guest libc 版本落后于真机**，
与配方、上游代码、依赖制品都无关 —— 属 pitfall T017 的 loader 类。
处置：按 T017 在**环境侧**补 shim 反证（`/opt/ohos-guest/lib/libarc4shim.so`
已有；另在容器侧自建一个导出 `__fd_chk(int)` 的 shim），**shim 不进配方**。
补 shim 后同一条二进制 `rc=1` 且输出符合预期（见 §7）。

### 9.2 CI 的 L2 冒烟对本包必然是 `warn`

L2 会依次尝试 `xcolmix --version` 与 `xcolmix --help`。xcolmix 无 `--version`
开关：两者都会落到 `argc==2` + `access()` 失败的 usage 分支，退出码 1，
于是 L2 记 `warn`（**非阻塞**，门禁不因此失败）。为让 L2 变绿而给上游加版本
开关属于与任务无关的功能新增，故不做，如实记录。

### 9.3 ELF 签名

HarmonyOS 内核拒绝执行未签名 ELF。`package()` 里对 `bin/xcolmix` 做
`llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1`，
两个工具都只在真机 worker 上存在，找不到时跳过（交叉构建宿主不需要）。
同时对拷进包目录的可执行文件做一次重新落地 + `chmod +x`（pitfall T105：
真机 HMDFS 下 `make install` 落地的可执行文件可能带内核级不可执行标记，
`chmod` 无效，重新拷贝才是有效修法）。

## 10. 已知限制

- `src/xcolmix.c` 里 `rgbfile` 的默认值 `/usr/lib/X11/rgb.txt` 是上游写死的
  系统路径，未做可重定位化：改它会变更上游默认行为。命令行参数
  `xcolmix <rgb-database-file>` 已由测试断言覆盖，实际使用时可显式指定。
- xcolmix 是 X11/XForms 图形程序，本平台需经 XWayland 提供 X server 才能显示
  窗口；构建与本包的全部断言均不依赖 X server。
