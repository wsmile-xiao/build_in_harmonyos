# nuvie 0.5 — autotools 消费者的依赖 flags 有两条互不替代的通路（草稿）

**Category**: build, autotools, conan, sdl, portability · **Severity**: 3 · **Tool**: conan/configure/make

## 症状

1. `configure` 报 `*** SDL version 1.2.0 not found!` / `checking for sdl-config... no`
   —— 尽管 `self.requires("sdl12-compat/1.2.68")` 写得好好的，包也构建了。
2. 或 configure 报 `can't find guile. This software REQUIRES guile.` —— 尽管
   guile 已在依赖图里。
3. 或 configure 通过，make 期 `SDL.h: No such file or directory` /
   `undefined reference to 'SDL_*'`。
4. configure 日志里「依赖路径全对」（`-L`/`-I` 都在 conanbuild env 里）+「却报找不到 X」
   同时出现。

## 根因

`self.requires("X/1.2.3")` 只是把依赖加进依赖图，**不会**自动产生任何编译/链接参数。
参数由 generator 产出：autotools 侧是 `AutotoolsDeps`（→ `CPPFLAGS`/`LDFLAGS`/`LIBS`）
与 `AutotoolsToolchain`（→ `--host`/`--build` 等）。漏写 `generate()` 里那句
`AutotoolsDeps(self).generate()` 时，构建**看起来**正常（依赖被构建、`conanbuild`
环境里有 `LD_LIBRARY_PATH`），但 configure/make 一个 `-I`/`-L`/`-l` 都拿不到。

更隐蔽的是 SDL 1.2 这一支：**它根本不走 `CPPFLAGS`/`LIBS`**。`AM_PATH_SDL` 展开后是

```m4
AC_PATH_PROG(SDL_CONFIG, sdl-config, no, $PATH)
SDL_CFLAGS=`$SDL_CONFIG ... --cflags`
SDL_LIBS=`$SDL_CONFIG ... --libs`
```

即 SDL 的 flags **只能**来自 `SDL_CONFIG` 指向的那个**可执行脚本**。上游再自己把它
拼进别的变量，例如 nuvie：

```make
# configure.ac:136
CXXFLAGS="$CXXFLAGS $DEBUG_FLAGS $SDL_CFLAGS"
# Makefile.am:6
LDFLAGS  = @LIBS@        # SDL_LIBS 经 LIBS 被搬进 LDFLAGS
```

`AutotoolsDeps` 注入的那三个变量里**不会**出现 SDL 的 `-lSDL-1.2`。

于是同一份配方里存在**两条互不替代的通路**：

| 通路 | 覆盖 | 注入方式 |
|---|---|---|
| (A) SDL 脚本 | `AM_PATH_SDL` / 直接调 `sdl-config` 的上游 | `SDL_CONFIG=<build_folder>/sdl-config`（绝对路径）+ `PATH` + `LD_LIBRARY_PATH` |
| (B) AutotoolsDeps | `AC_CHECK_LIB` / `AC_CHECK_HEADER` / `PKG_CHECK_MODULES` 的上游 | `generate()` 里 `AutotoolsDeps(self).generate()` → `CPPFLAGS`/`LDFLAGS`/`LIBS` |

- **只做 (A)**：依赖面一宽就炸。ballandpaddle 的 guile 上游是
  `AC_CHECK_LIB(guile, scm_boot_guile, LIBS="-lguile $LIBS", AC_MSG_ERROR(can't find guile...))`，
  **没有 pkg-config 兜底**，探针读的正是 (B) 那条通路。
- **只做 (B)**：连 SDL 都找不到（`AC_PATH_PROG` 返回 `no`）。

## 处置（可复用）

### 1. 先定位消费该 flag 的宏，再决定走哪条通路

```sh
grep -n 'AM_PATH_SDL\|AC_CHECK_LIB\|AC_CHECK_HEADER\|PKG_CHECK_MODULES' configure.ac
grep -n 'SDL_CFLAGS\|SDL_LIBS\|@LIBS@' configure.ac Makefile.am
```

判据与具体库无关：**看是哪个宏在消费这个 flag**。

### 2. 两条都保留

不要因为"已经有外壳了"删掉 `AutotoolsDeps`，也不要因为"`AutotoolsDeps` 已经注入了
`-L`/`-l`"就以为 SDL 不用管 —— 它们覆盖的是**不同的宏**。

`generate()` 里的规范顺序（见 `archives/s/sdl_image/1.2.12`，仓库 296 个配方同此写法）：

```python
def generate(self):
    AutotoolsDeps(self).generate()
    AutotoolsToolchain(self).generate()
```

### 3. `LD_LIBRARY_PATH` 与 `CPPFLAGS` 也是两码事

配方里 `_environment_prefix()` 汇总的 `LD_LIBRARY_PATH`（保证运行期/链接期找得到 `.so`）
**不能**替代 `CPPFLAGS`（保证编译期找得到头文件）。缺头文件时 `-I` 不会从
`LD_LIBRARY_PATH` 来。

### 4. 识别信号

configure 日志里「依赖路径全对」+「却报找不到 X」，或 configure 通过但 make 期
`SDL.h: No such file or directory` —— 都是「探针/编译器看的变量」与「你注入的变量」
不是同一个。

## 与同族草案的分工

- `DRAFT-7348-ballandpaddle-0.8.1-sdl12-compat-has-no-sdl-config`：讲 **(A) 通路本身
  为什么需要外壳**（`sdl12-compat` 包里没有 `sdl-config` 脚本，`AC_PATH_PROG` 对已
  赋值的绝对路径 `SDL_CONFIG` 直接采信）。
- **本条**：讲 **(A) 与 (B) 的分工** —— 造了外壳 ≠ 配好了依赖，反之亦然。

两者互补，不重复。

## 验证

nuvie 0.5 实测：两条通路都在（`_write_sdl_config()` + `generate()` 里的 `AutotoolsDeps`）。
`test_package` 实跑安装后的 `bin/nuvie`，stderr 出现 `Couldn't initialize SDL:`
（`screen/Screen.cpp:117`，`SDL_Init` 返回负值时打印），同时证明 `libSDL-1.2.so`
及其传递依赖全部加载成功、链接期与运行期一致。

## 关联

- `archives/s/sdl_image/1.2.12/conanfile.py`（`generate()` 顺序的规范先例）
- `archives/b/ballandpaddle/0.8.1/conanfile.py`（对偶案例：guile 走 (B) 通路）
- `knowledge/drafts/DRAFT-6380-nuvie-0.5-headless-interactive-binary-assertions.{kv,md}`
