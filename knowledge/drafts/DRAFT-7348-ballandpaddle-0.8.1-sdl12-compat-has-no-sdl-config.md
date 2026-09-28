# SDL 1.2 时代的 autotools 工程找的是 `sdl-config` **脚本**，而 `sdl12-compat` 包里没有它——依赖全装对了，configure 照样报「SDL not found」

> DRAFT-7348-ballandpaddle-0.8.1-sdl12-compat-has-no-sdl-config
> （知识库扩展草稿，路径 B）与 ballandpaddle 0.8.1 归档同 PR 交付。

ballandpaddle（GNU Ball and Paddle）是个 2008 年的打砖块游戏：SDL 1.2 渲染、
内嵌 Guile 1.8/2.2 跑 Scheme 关卡脚本。它的 `configure` 走 `AM_PATH_SDL`，而
`AM_PATH_SDL` **不是** `pkg-config` —— 它去 `PATH` 里找一个叫 `sdl-config` 的
**可执行脚本**，然后执行它取 flags。

问题在于：当代的 OHOS 依赖仓里只有 `sdl12-compat`（SDL 1.2 ABI 兼容层，
跑在 SDL2 之上），它**刻意不提供 `sdl-config`**。

于是出现一个非常容易误判的现场：

```
checking for sdl-config... no
checking for SDL - version >= 1.2.0... no
configure: error: *** SDL version 1.2.0 not found!
```

而同一次 configure 的 `CPPFLAGS` / `LDFLAGS` 里，`-I<dep>/include/SDL` 与
`-L<dep>/lib -lSDL-1.2` **都好好地在那儿**。

> **第一反应通常是「依赖没装上」，但这里是「探针找错了东西」。**
> 这是 E 族「探针与制品不符」的第二类变体：探针找的不是**库**，是一个
> **构建期可执行脚本**。库层面的 `-L`/`-l`/`-I` 对不对，与它完全无关。

---

## 一、先确认探针找的是什么（两分钟判据）

```bash
# 工程侧：它靠 sdl-config 还是 pkg-config？
grep -n 'AM_PATH_SDL\|sdl-config' configure.ac aclocal.m4 configure | head
#   有输出 → 全部 flags 来自执行 sdl-config。此时 PKG_CONFIG_PATH 怎么设都没用。

# 制品侧：这个环境的 SDL 里到底有没有 sdl-config / sdl.pc？
find <sdl12-compat-prefix> -name 'sdl-config' -o -name 'sdl.pc'   # → 无输出
ls -l <sdl12-compat-prefix>/lib/libSDL-1.2*                       # → libSDL-1.2.so / .a

# 依赖其实已经注入了（证伪「依赖没装」）
grep -rn -- '-lSDL-1.2' <build_folder>/*.sh | head
```

`AM_PATH_SDL` 展开后的骨架（来自上游 `aclocal.m4`）：

```m4
AC_PATH_PROG(SDL_CONFIG, sdl-config, no, [$PATH])
...
SDL_CFLAGS=`$SDL_CONFIG $sdlconf_args --cflags`
SDL_LIBS=`$SDL_CONFIG $sdlconf_args --libs`
AC_SUBST(SDL_CFLAGS)
AC_SUBST(SDL_LIBS)
```

注意 `$sdlconf_args` / `$sdl_args` 在这个宏里通常是**空**的，所以脚本收到的
`$1` 就是 `--cflags` / `--libs` 本身。

---

## 二、修法：在 build_folder 造一个外壳，用**绝对路径**注入

核心就三步，全部发生在构建期环境，**不碰上游源码、不给 sdl12-compat 打补丁**：

```python
def _write_sdl_config(self):
    dep = self.dependencies.host["sdl12-compat"]
    prefix = dep.package_folder
    shim = os.path.join(self.build_folder, "sdl-config")
    save(self, shim, textwrap.dedent(f"""\
        #!/bin/sh
        case "$1" in
          --version)                  echo 1.2.68 ;;
          --prefix|--exec-prefix)     echo {prefix} ;;
          --cflags)                   echo -I{prefix}/include/SDL ;;
          --libs|--static-libs)       echo -L{prefix}/lib -lSDL-1.2 ;;
          *) exit 1 ;;
        esac
        """))
    # 共享文件系统常常不保留 exec 位（save() 默认 0644）
    os.chmod(shim, stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return shim
```

注入两路：

```python
prefix = (f"SDL_CONFIG='{shim}' "
          f"PATH='{build_folder}:<dep bins>:$PATH' "
          f"LD_LIBRARY_PATH='<dep libs>:$LD_LIBRARY_PATH'")
```

### 两个必须知道的细节

**① `SDL_CONFIG` 必须绝对路径。** `AM_PATH_SDL` 用 `AC_PATH_PROG`，而
`AC_PATH_PROG` 的语义是「**变量已非空则不覆盖**」。预置一个绝对路径即可绕开
`PATH` 查找 —— 这不只是省事，也是唯一稳妥的方式（避免另一个依赖捎带的
同名 `sdl-config` 被选中）。相对路径不可靠：子目录里的 `Makefile` 重跑
configure 规则时 cwd 就变了。

**② 仍然要把外壳目录前置进 `PATH`。** ballandpaddle 走宏，但同族工程里
有些构建脚本是**直接**调 `sdl-config` 的，两路都铺才稳。

---

## 三、外壳里两个「看起来无害」的写法其实会埋雷

```sh
*) exit 1 ;;                       # ✅ 未知开关直接失败
*) echo ""; exit 0 ;;              # ❌ 静默通过
```

如果未知开关 `exit 0` 打印空串，`AM_PATH_SDL` 会拿到**空的**
`SDL_CFLAGS` / `SDL_LIBS` **且不报错**，configure 顺利通过 —— 失败被推迟到
编译期（`SDL.h: No such file or directory`）或链接期
（`undefined reference to SDL_Init`）。现场离根因隔了好几屏日志。

同理，`os.chmod` 那一步不能省。共享文件系统（HMDFS 等）不保留 tarball 里的
可执行位，`save()` 写出的文件是 0644，configure 会报：

```
./build/sdl-config: Permission denied
```

又是一个「看着像环境/权限问题、其实是本包问题」的症状。**一个外壳脚本能产出
三种彼此无关的错误信息**，这就是它值得写进知识库的原因。

---

## 四、同类信号：`*-config` 脚本 vs `.pc` 文件

这不是 SDL 独有。老式 autotools 库普遍提供 `*-config` **脚本**取 flags，
而现代打包往往只发 `.pc`：

| 脚本 | 常见缺失场景 |
|------|-------------|
| `sdl-config` | 只有 `sdl12-compat` / SDL2 的环境 |
| `sdl2-config` | 只发 `sdl2.pc` 的打包 |
| `xml2-config` | 部分轻量打包 |
| `curl-config` | 静态链接特化包 |
| `ncursesw6-config` / `gtk-config` / `freetype-config` | 名称随 soname 漂移，脚本名对不上 |

**统一的识别信号**：探针查的是 `PATH`（`AC_PATH_PROG`），而不是 `pkg-config`
（`PKG_CHECK_MODULES`）。看 configure 输出里是
`checking for sdl-config...` 还是 `checking for SDL...`（后者内层会调 pkg-config）
就能分辨。

与 `DRAFT-7348-ballandpaddle-0.8.1-ac-check-lib-probes-a-fixed-soname` 是同一个
母题的两种形态：

- 那条：探针按**写死的 soname** 找库（`-lguile` vs `-lguile-2.2`）
- 这条：探针按**可执行脚本名**找库（`sdl-config`）

两者的共同判据都是：**依赖已经注入好了，但探针在找不存在的东西。**
避开它们的共同前提也是同一个：先看探针找的**是什么类别的东西**，再怀疑依赖。

---

## 复现清单

```bash
# 1) 探针类别
grep -n 'AM_PATH_SDL\|PKG_CHECK_MODULES.*SDL\|sdl-config' configure.ac configure | head
# 2) 制品提供面
find <sdl12-compat-prefix> -name 'sdl-config' -o -name 'sdl.pc'   # 期望：无输出
ls -l <sdl12-compat-prefix>/lib/libSDL-1.2*
# 3) 依赖其实注入了
grep -rn -- '-lSDL-1.2' <build_folder>/*.sh | head
# 4) 修复生效
grep -n 'checking for sdl-config' config.log        # 期望回显绝对路径
grep -n 'SDL_CFLAGS\|SDL_LIBS' config.log | head    # 期望非空
<build_folder>/sdl-config --cflags                  # → -I<dep>/include/SDL
<build_folder>/sdl-config --libs                    # → -L<dep>/lib -lSDL-1.2
```
