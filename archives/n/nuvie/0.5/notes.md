# nuvie 0.5 适配笔记

## 背景

Nuvie 是 Origin 三款游戏（Ultima 6 / Martian Dreams / The Savage Empire）的开源引擎，
首版 2003 年，0.5 版 tarball 出自 2014-03-14（`configure` 自报 `nuvie 0.5svn`，
游戏内版本串 `Nuvie: ver 0.5 rev 1927`），GPL-2.0-or-later。

它是「1990 年代 C++ + SDL 1.2」这一类上游的典型样本：**外部依赖只有一条 SDL 1.2**。
Lua 5.1、adplug、SDL_mixer 的解码器（libmikmod / timidity / 等等）、BMP/PCX 解码
全部以源码副本内嵌在 tarball 里，不走外部包管理器。所以适配面很窄，就两件事：

1. 把 SDL 1.2 接上（上游用 `AM_PATH_SDL` 找 `sdl-config` **可执行脚本**，
   而 ohpcd 只发布 `sdl12-compat`，包内没有该脚本）；
2. 把 2014 年的 autotools 产物在 OHOS 的 HMDFS + musl 上跑通。

`tools/` 下 7 个 `noinst_PROGRAMS` 是给开发者从原版游戏磁盘拆数据文件用的辅助
程序，既不安装也不参与游戏运行，用上游自带的 `--disable-tools` 关掉（省掉大半
构建时间）。

## 依赖面

| 依赖 | 版本 | 作用 |
|---|---|---|
| sdl12-compat | 1.2.68 | 提供 `libSDL-1.2`（SDL2 之上的 1.2 ABI 兼容层） |

仅此一条。Lua / adplug / mixer / 各类解码器均为随源码分发的内嵌副本。

## 补丁

### 0001-configure-umask.patch（可移植性，平台专属）

`configure`（以及它写进 `config.status` 的同一段文本）用
`(umask 077 && mktemp -d "./confXXXXXX")` 在 cwd 建临时目录。HMDFS 挂载下
0700 目录对构建进程不可写（chmod 不生效），表现为 configure 打印成功但 Makefile
从未生成，或后续 `./confXXXXXX/subs-1.sed: Permission denied`。

本包 `configure` 里 `umask 077` 出现 **2 处**（`mktemp -d` 主路径与其 `mkdir`
回退路径），两处都改为 `022`。同仓库先例：`archives/s/sdl_image/1.2.12` 的
`0001-configure.patch`（`patches/0002` 里的同名修复）、
`archives/b/ballandpaddle/0.8.1`、`archives/n/ncdc/1.25`，
知识库条目 **E011**。

**两处改动必须合并进同一个 hunk。** 最初写成 `@@ -5651,7` + `@@ -5656,7` 两个
hunk，后者起点 5656 落在前者覆盖的 5651..5657 之内。Conan 用 `patch_ng` 打
补丁，它校验 hunk 时对源文件**只扫一遍**：hunk0 校验到 5657 时把 `hunkno` 推进
到 1，但 `hunkfind` 只在 `行号 == hunk.startsrc` 时才重算，而 5656 已经走过，
于是 `hunkfind` 一直保留 hunk0 的 7 行、`hunklineno` 继续自增，下一行就在
`patch_ng.py:1142` 抛 `IndexError: list index out of range`。GNU `patch(1)` 能打
这种补丁（它按 hunk 逐段重新定位），`patch_ng` 不能。合并成
`@@ -5651,12 +5651,12`、单 hunk 覆盖 5651..5662 后即可正常校验。CI 失败原文：
`nuvie/0.5: Error in build() method, line 81 / apply_conandata_patches(self) /
IndexError: list index out of range`。

### 0002-nuvieDefs-clamp-avoid-macro.patch（可移植性，非平台专属）

`nuvieDefs.h:52` 把 `clamp` 定义成**三参函数式宏**：

```c
#define clamp(v, c1, c2) ( ((v) < (c1)) ? (c1) : (((v) > (c2)) ? (c2) : (v)) )
```

libc++（OHOS 工具链的 C++ 标准库）在 `<algorithm>` / `__algorithm/clamp.h`
里声明 `std::clamp`，其中有一个**四参**重载。函数式宏会把之后每一次对该名字的
书写都在预处理期吃掉，于是那条声明被宏展开而不是被解析：调用点参数过多、本该
声明的形参名消失，任何**传递性**包含到 `<algorithm>` 的翻译单元都编译不过。
`actors/Actor.cpp` 经 `U6misc.h` / `Actor.h` 拉进 C++ 头文件后即命中。CI 原文：

```
.../libcxx-ohos/include/c++/v1/__algorithm/clamp.h:27:57: error: too many
    arguments provided to function-like macro invocation
.../clamp.h:29:28: error: use of undeclared identifier '__hi'
.../clamp.h:32:2: error: expected ';' at end of declaration
2 warnings and 9 errors generated.
make[2]: *** [Makefile:1563: Actor.o] Error 1
```

修法：C++ 下把 `clamp` 改为**同名真函数**（`#ifdef __cplusplus` / `#else` / `#endif`
包住原宏），真函数与任何声明都不冲突。这是行为保持的：全树调用点传的都是整型
（`clamp(val,-127,dex)`、`clamp(goal.x-loc.x,-1,1)`、`clamp(atoi(...),0,9)`、
`clamp(opacity,0,255)` …），宏的条件表达式本来就按常规算术转换（即 `int`）求值，
故 `static inline int clamp(int, int, int)` 语义不变。

全树唯一有 `using namespace std;` 的文件是 `misc/U6misc.cpp`，它从不调用
`clamp()`，因此该全局函数不会与 `std::clamp` 构成二义。C 侧保留宏不变。

> 命名冲突类型：**函数式宏 vs C++ 标准库同名实体**。与「宏遮蔽关键字」不同，
> 这里宏本身在 C 里是对的，问题只出在 C++ 传递包含 `<algorithm>` 时；因此补丁
> 用 `__cplusplus` 分叉而不是删掉宏。

## 构建处理

| 问题 | 处理 |
|---|---|
| 上游调 `sdl-config`，ohpcd 只发布 sdl12-compat（无该脚本） | `_write_sdl_config()` 在 build_folder 写一个 `sdl-config` 外壳（`--version/--prefix/--cflags/--libs`），经 `SDL_CONFIG` + `PATH` 注入。`AM_PATH_SDL` 用 `AC_PATH_PROG(SDL_CONFIG, sdl-config, no, $PATH)` 找它，但**对已按绝对路径赋值的 `SDL_CONFIG` 直接采信**，所以外壳路径必须绝对。同款做法见 `archives/s/sdl_image/1.2.12` |
| 上游 2011 年的 `config.guess`/`config.sub` 不认识 HarmonyOS | configure 显式 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`（gnu 三元组）；设备侧 clang 的真实 target 仍由 conan profile 决定 |
| OHOS HMDFS 不保留 tarball 里的可执行位 | `_restore_helper_modes()` 给 `configure`/`config.guess`/`config.sub`/`install-sh`/`missing`/`depcomp` 补 `+x` |
| **补丁打的是已生成的 `configure`，mtime 会被 patch 改写成 diff 头时间戳** | 见下节 |
| OHOS 沙箱不支持 mkfifo，jobserver 会炸 | `make -j1` |
| `tools/` 7 个 noinst_PROGRAMS 纯属开发者工具 | `--disable-tools`（上游自带开关，`configure.ac:63`） |
| **上游只支持 in-tree 构建，conan 默认 out-of-tree** | `build()`/`package()` 的 configure/make/install 全部 `cwd=self.source_folder`，见下节 |
| `screen/Scale.inl` 三处 `register int r = 0;`（323/512/794 行）在 profile 的 `cppstd=17` 下是 **hard error** | `error: ISO C++17 does not allow 'register' storage class specifier [-Wregister]`，`make` 在编译 `Scale.o` 时停下（CI 日志 `nuvie/0.5: ERROR: Error in build() method, line 121`）。上游 0.5（2011）不会为 C++17 回头改，构建期在 `AutotoolsToolchain.extra_cxxflags` 追加 `-Wno-register` 关掉该诊断，零补丁。同仓库先例：`archives/f/freeimage/3.18.0`（`-Wno-register`）、`archives/b/buddy/2.4`（`-Wno-error=register`） |
| `screen/Screen.cpp:1870/1886` 把 uint32 表达式写进聚合初始化的 `Uint16` 成员，C++11 起是 **hard error** | `error: non-constant-expression cannot be narrowed from type 'uint32' (aka 'unsigned int') to 'Uint16' (aka 'unsigned short') in initializer list [-Wc++11-narrowing]` ×4（两行各 2 处），`make` 停在编译 `Screen.o`。C++98 时代这只是 warning，0.5（2011）不会回头改；同样按构建期旗标追加 `-Wno-c++11-narrowing`。同仓库先例：`archives/b/ballandpaddle/0.8.1`（同一作者的项目，旗标完全相同） |
| `Look.cpp:40` / `Map.cpp:47` 把字符常量写进**指针**数组元素，clang 是 **hard error** | `error: incompatible integer to pointer conversion assigning to 'const char *' / 'uint8 *' from 'char'`，`make` 分别停在编译 `Look.o`、`Map.o`。`Look.h:31` 是 `const char *look_tbl[2048];`（写 `look_tbl[2047] = '\0';`）、`Map.h:125` 是 `uint8 *dungeons[5];`（写 `dungeons[4] = '\0';`）——C 里合法，C++ 里不是。上游 master 已都改为 `NULL`，构建期用 `replace_in_file` 做同一处替换（见下）。**这两处是分批暴露的**：先只撞到 `Look.cpp`，修好后 `make` 继续推进才撞到 `Map.cpp`（CI 09:48 `Map.o` Error 1），所以一次把全树同型处都覆盖掉；全树其余 `xxx[i] = '\0';`（Converse / GameClock / Magic / SaveGame / Event / Party / …）落点都是 **char 缓冲区**，语义正确，不能动。 |

### `Look.cpp` / `Map.cpp` 的 `'\0'` 指针终结为什么用 `replace_in_file` 而不是第三个补丁文件

前两处可移植性修改都以 `patches/000N-*.patch` 落盘，这一处刻意不走补丁：

* 0.5 tarball 的 `Look.cpp` 与上游 master **行号不对齐**（master 的构造函数里
  多一行空行，同一语句在 master 是第 41 行、在 0.5 是第 40 行）。按行号+hunk
  上下文写补丁，就得先拿到 0.5 的原文；而 tarball 源在 SourceForge，本机取回
  时被 403/SSL 打断，无法核对上下文，只能靠猜 —— 猜错就是 `patch` 失败，
  比不改还糟。
* 该处修改是**单行等价替换**（`'\0'` → `NULL`），没有跨文件的上下文漂移问题，
  `replace_in_file(..., strict=True)` 按内容锚定：找不到就报错，绝不会静默跳过。

所以补丁文件用于「有上下文、需要留档的源码级改动」，而这类单行、无上下文的
等价修复用内容锚定替换更稳。

### nuvie 只支持 in-tree 构建（本包第二处非显然耦合）

上游 `Makefile.am:5` 把工程内 include 目录写成**裸相对路径**：

```
CXXFLAGS = @CXXFLAGS@ -Iactors -IGUI -Imenus -Imisc -Ifiles -Ifonts -Iconf \
           -Ipathfinder -Iportraits -Isave -Iscreen -Iscript -Isound \
           -Isound/adplug -Isound/mixer -Itools -Iusecode -Iviews -Ilua -Ikeybinding
```

这些 `-I` 相对 **cwd** 解析，而上游源码树把这些子目录放在**顶层**
（`actors/`、`misc/`、`GUI/`…，`actors/Actor.cpp:27` 直接 `#include "U6misc.h"`
去够 `misc/U6misc.h`）。也就是说 Makefile 假定 `srcdir == builddir == cwd`。

conan 的 `basic_layout()` 默认 out-of-tree（VPATH）：autoconf 用 `am__isrc`
把 srcdir 指到 source_folder，cwd 却是 build_folder，于是命令行里出现的
`-Iactors -Imisc …` 全部落空、`$(srcdir)` 前缀只加在源文件路径上，
编译 `actors/Actor.cpp` 时找不到 `misc/U6misc.h`：

```
.../b/actors/Actor.cpp:27:10: fatal error: 'U6misc.h' file not found
     #include "U6misc.h"
make[2]: *** [Makefile:1563: Actor.o] Error 1
```

（日志里可以同时看到 `-I. -I<srcdir>` 与 `test -f 'actors/Actor.cpp' ||
echo '<srcdir>/'` 的 VPATH 回退串——`am__isrc` 只在 srcdir≠builddir 时才展开成
`-I$(srcdir)`，这本身就是 VPATH 的证据。）

修法：三处 `self.run()` 显式 `cwd=self.source_folder`（configure / `make -j1` /
`make install DESTDIR=…`），回到上游唯一支持的模式。conan 的 `run(env="conanbuild")`
只是 `. "<abs>/conanbuild.sh" && <cmd>`，不 `cd`，所以 `cwd` 会如实生效。
`_write_sdl_config()` 仍写在 build_folder（`SDL_CONFIG` 用的是绝对路径）。

### 依赖 flags 有两条**独立**通路，缺一不可

- **SDL 那一路走 `sdl-config` 外壳**：`AM_PATH_SDL` 把
  `` `$SDL_CONFIG --cflags` `` 拼进 `CXXFLAGS`（`configure.ac:136`），
  把 `` `$SDL_CONFIG --libs` `` 拼进 `SDL_LIBS` → `LIBS`；
  而 `Makefile.am` 里 `LDFLAGS = @LIBS@` 又把它转进链接行。
- **其余 host 依赖走 `AutotoolsDeps`**：`generate()` 里
  `AutotoolsDeps(self).generate()` 把 `-I/-L/-l` 注入
  `CPPFLAGS/LDFLAGS/LIBS` 并落进 conanbuild 环境。本包 host 依赖只有
  sdl12-compat 一条、且它的 flags 走外壳，但 `_environment_prefix()` 汇总的
  `LD_LIBRARY_PATH` 与 `AutotoolsDeps` 生成的 `CPPFLAGS` 是**两条独立通路**，
  缺了 `AutotoolsDeps` 会在别处（传递依赖、未来的 sdl_image/sdl_mixer 面）
  掉链子，故按仓库 296 个配方的统一写法保留。

### mtime 归一化（`_keep_generated_newer`）

`patches/0001` 改的是**已生成的** `configure`。GNU patch 会把被打补丁文件的
mtime 设成 diff 头里的时间戳，于是 `configure` 可能比 `configure.ac` /
`aclocal.m4` 旧；根 `Makefile.in` 里有两条重生成规则：

```make
$(top_srcdir)/configure: $(am__configure_deps)   # = configure.ac + aclocal.m4
$(srcdir)/config.h.in:   $(am__configure_deps)   # -> $(AUTOHEADER)
```

mtime 一倒挂，`make` 就会去重跑 `autoconf` / `autoheader` —— 沙箱里没有它们，
直接失败。处理：先把 autotools 输入（`configure.ac`、`aclocal.m4`、
`Makefile.am`、`tools/Makefile.am`）统一 `touch -d '2000-01-01 00:00:00'`，
再把生成物 touch 成当前时间。

**本包比先例多一件：`config.h.in` 必须一起 touch。** 上游用 automake 1.11.2，
它生成的 `Makefile.in` 里 `config.h.in` 走 `$(AUTOHEADER)` 重建（本包
`config.h.in` 只有 791 字节、内容极少，正说明它是 autoheader 产物而非手写）；
先例 libmodbus / ballandpaddle 的输入清单里没有它，本包补上。
生成物清单：`configure config.h.in Makefile.in tools/Makefile.in`。

## 测试账本

| 维度 | 数量 |
|---|---|
| 上游静态声明（`TESTS` / `check_PROGRAMS`） | 0 |
| 构建系统注册（automake check 目标） | 0 |
| 上游实际执行 | 0 |
| 新增消费者断言（`test_package/test_nuvie.sh`） | 29 |

上游确无测试套件：`Makefile.am` / `tools/Makefile.am` 里没有 `TESTS`、没有
`check_PROGRAMS`，`check` 目标只按 `SUBDIRS = tools` 递归；`tools/` 下全是
`noinst_PROGRAMS` 开发者数据拆分工具（本配方已关闭），`data/` 是 12 个 UI
边框/滚动条 `.bmp` + 4 个按键映射 `.txt`。证据链见 `test_package/MANIFEST.yml`。

**未执行项**：真正的游戏主循环（SDL 开窗 + Ultima 6 数据文件加载）。
CI 沙箱无显示设备；且 Ultima 6 原始游戏数据受版权保护、不随本包分发，
无法在测试期提供合法输入。故本脚本只断言运行期资产**已安装且非空**，
不把它计入通过率。

### 无 CLI 的交互式程序怎么写出确定性断言

nuvie 没有 `--version` / `--help`（`argv[1]` 只接受游戏代号），且是交互式全屏
程序 —— 天真地跑一下会挂在 SDL 事件循环里。本脚本用**两条必然自行退出的
早期失败路径**构造确定性断言，关键前提读自源码：

```
Nuvie::init()
  ├─ initConfig()                  nuvie.cpp:216
  │    失败 → DEBUG "No config file found!" → return false        ← 路径 B
  └─ screen = new Screen(config); screen->init()
       Screen::init() 里 SDL_Init(SDL_INIT_VIDEO) 失败
              → DEBUG "Couldn't initialize SDL: %s"  screen/Screen.cpp:117
       → DEBUG "Initializing screen!" → return false              ← 路径 C
  ... 以上全部失败路径之后才 ConsoleInit(...) 设置 g_console
```

而 `main()` 在 `init() == false` 时走 `ConsolePause(); return 1;`
（`main.cpp:73-77`），`ConsolePause()` 的实现是：

```c
void ConsolePause()
{
	if(g_console == NULL)
		return;      // ← Console.cpp:113-114
	...SDL_WaitEvent...
}
```

**`g_console` 只有在 `ConsoleInit()` 之后才非空，而两条失败路径都在它之前
返回** → `ConsolePause()` 立即返回 → 进程以退出码 1 确定性退出，不挂死。

- **路径 B**：`( unset HOME; exec "$BIN" )`，cwd 里也没有 `nuvie.cfg`。
  `initConfig()` 里 `if(home_env != NULL && initDefaultConfigUnix(home_env))`
  （`nuvie.cpp:279`）对 HOME 未设置做了显式守卫，所以这条路径安全且确定。
- **路径 C**：HOME 指向可写空目录（`initDefaultConfigUnix` 会生成
  `$HOME/.nuvierc` 并 `config->write()` 写回），同时
  `SDL_VIDEODRIVER=nuvie_no_such_driver` 指向一个不存在的视频驱动 ——
  无论沙箱有没有显示设备，`SDL_Init(SDL_INIT_VIDEO)` 都确定性失败。

路径 C 额外套一个 30 秒 `run_bounded` 兜底（`kill -0` 轮询，超时 `kill -9`
返回 124），防止将来上游行为变化把脚本挂死。脚本**刻意不用 `set -e`**：
它要后台起进程再按秒轮询，`set -e` 会让 `wait` 的非零返回直接终止脚本而不是
记一条 FAIL；所有判定都走显式 `ok`/`bad` 记账。

### 为什么其中 10 项断言是「鸿蒙特有测试」

29 项断言里，**B 组（无配置路径 5 条）+ C 组（配置加载 + SDL 初始化路径 5 条）
共 10 条**是鸿蒙特有的（其余 19 条：A 组 1 条可执行性、D 组 18 条安装布局，
在别的平台同样成立）。

这 10 条必须**真实执行已安装的 OHOS aarch64 二进制**才能拿到输出，因此
「能跑出这些 stderr 行」同时证明：

1. 该 ELF 在 OHOS 上被动态加载器接受 —— `libSDL-1.2.so` 等全部 NEEDED
   （含 sdl12-compat 的传递依赖 SDL2）解析成功；漏一个会在 `main()` 之前被
   拒绝，退出码是 127/126 而非 1，stderr 是 `cannot open shared object`
   这种**另一种文本**（B 组两条 `check_not` 正是这条判据）；
2. 符号全部解析成功（`-lSDL-1.2` 的链接期与运行期一致；B 组
   `check_not "undefined symbol"`）；
3. `main()` → `Nuvie::init()` → `initConfig()` 的 C++ 代码在 OHOS 上真实执行：
   B 组断到 `Debugging enabled`（`main.cpp` 的启动日志）与
   `No config file found!`（initConfig 失败诊断），C 组断到
   `Loading Config from`（配置读取）与 check_any 的「执行到 Screen/SDL 段」
   —— libSDL-1.2 已加载且 `SDL_Init` 真实被调用并返回错误；
   另外核对 `initDefaultConfigUnix` 真的在 OHOS 文件系统上写出了
   非空的 `$HOME/.nuvierc` —— 即 HMDFS 的写路径可用。

   ★ C 组的 SDL 错误文案由**平台实测**决定，不能照抄源码字符串。CI #62596
   的实跑输出是：

   ```
   <[E] set_safe_video_settings nuvie.cpp:400>
   Couldn't initialize SDL_VIDEO!
   ```

   即走的是 `set_safe_video_settings`（`nuvie.cpp:400`）而不是 `Screen::init`
   里那句 `Couldn't initialize SDL: %s`（`screen/Screen.cpp:117`）——
   OHOS/sdl12-compat 上 `SDL_Init(SDL_INIT_VIDEO)` 对不存在的
   `SDL_VIDEODRIVER` **不返回负值**，执行流被推到更后面的视频设置函数。
   因此 `test_nuvie.sh` 的 check_any 模式写成不带尾部标点的
   `Couldn't initialize SDL`，一次覆盖两种写法（原先只写
   `Couldn't initialize SDL:` 会误判 FAIL）。

所有 DEBUG 输出走 `fprintf(stderr, ...)`（`Debug.cpp:78-96`），
`Debug.cpp` 默认 `CurrentDebugLevel = LEVEL_DEBUGGING(7)`，所以 `DEBUG(0,...)`
与 `DEBUG(1,...)` 全部会打印 —— 断言所依赖的每条文本都在默认配置下可见。

`test_package/conanfile.py` 聚合了全图依赖的 libdir 进 `LD_LIBRARY_PATH`
（VirtualRunEnv 不覆盖传递依赖，ncdc CI #44337 先例），并用 `bash` 包一层
（OHOS `/system/bin/sh`（mksh）不能可靠执行 ELF 二进制）。
