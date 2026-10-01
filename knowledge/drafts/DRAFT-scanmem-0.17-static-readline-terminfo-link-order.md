# DRAFT-scanmem-0.17: 静态 readline 链接失败的真因是「依赖图没透传 ncurses」

## 症状

`readline/8.3` 是上游 configure 的**硬要求**（`AC_CHECK_LIB` 的 action-if-found
里直接 `exit 1`）。即使把 readline 的 include/lib 都正确喂给 configure，仍然：

```
checking for tgetent in -ltermcap... no
checking for readline in -lreadline... no
libreadline could not be found, which is required to continue.
```

手写 `-L<readline>/lib -lreadline` 复现，链接器给出的错误很有指向性：

```
ld.lld-15: error: undefined symbol: tputs
>>> referenced by display.c
>>>               display.o:(rl_redisplay) in archive .../lib/libreadline.a
ld.lld-15: error: undefined symbol: tgoto
ld.lld-15: error: undefined symbol: tgetnum
ld.lld-15: error: undefined symbol: tgetent
ld.lld-15: error: undefined symbol: tgetstr
ld.lld-15: error: undefined symbol: PC
ld.lld-15: error: undefined symbol: BC
ld.lld-15: error: undefined symbol: UP
```

## 根因

OHOS 上的 readline 是**纯静态**包（只有 `libreadline.a` / `libhistory.a`），
而 readline 的终端显示层需要 terminfo 的函数与**能力变量**。链接失败由两件事叠加：

1. **readline 配方的 `package_info()` 不透传 ncurses**

   ```python
   def requirements(self):
       self.requires("ncurses/6.6")
   def package_info(self):
       self.cpp_info.libs = ["readline", "history"]   # 没有 ncurses
   ```

2. **上游那条 termcap 探测是非致命的，失败就不管**

   ```m4
   AC_CHECK_LIB([termcap], [tgetent], [], [])   # action-if-found 为空
   AC_CHECK_LIB([readline], [readline], [], [ exit 1 ])
   ```

   `termcap` 探测失败不报错，也**不会**把 `-ltermcap` 塞进 `LIBS`，
   于是 terminfo 彻底无人提供。

值得强调：这不是「忘了加 `-lncurses`」那么简单。静态链接对**顺序**有要求
（消费者在前、核心提供者在后），手工把 terminfo 库放到 readline 之前会得到
`undefined reference to rl_redisplay` 这类反向错误。

## 最终方案

消费者只声明上游那个硬依赖，让**依赖图**去做透传：

```python
def requirements(self):
    self.requires("readline/8.3")
```

Conan 2 会把传递依赖的 `cpp_info.libs` 按拓扑序聚合进 LIBS，实测生成：

```
-lreadline -lhistory -lncursesw -lformw -lmenuw -lpanelw
```

顺序正确（readline 在前、ncursesw 在后），`configure` 与最终链接一次通过。
`ncurses/6.6` 的配方注释本身就写明了这条约定
（`# Static link order is consumers first, core provider last.`）。

**不要**去改上游那条 termcap 探测：它非致命本来就是为了让「没有 termcap 也能编」，
补它只会引入不必要的耦合。

## 一个必须分清的环境差异：`__fd_chk`

`nm -u libreadline.a` 会看到两条 `U __fd_chk`。先别急着改配方——去查**目标**
libc 导不导出它：

```bash
readelf -sW <真实 SDK>/sysroot/usr/lib/aarch64-linux-ohos/libc.so | grep -c __fd_chk
```

本次实测：真机 OHOS libc 命中 **1**（有），而本机 WSL guest 的
`/opt/ohos-guest/lib/libc.so` 命中 **0**（无）。于是本机跑任何链接了 registry
OHOS readline 的 aarch64 二进制都会 `Error relocating …: __fd_chk: symbol not found`，
而真机完全正常。

这类「构建机 libc 与目标 libc 的 fortify 符号差异」属于**运行期环境差异**，
要在真实 SDK sysroot 下复验，不要据此改配方。

## 适用边界

- **适用**：任何 `AC_CHECK_LIB` 硬要求 readline、且 readline 走 Conan 管理的项目。
- **不适用**：
  - readline 配方**已经**在 `package_info()` 里透传 ncurses 的情形——此时
    只需确认静态链接顺序，不要重复声明 ncurses；
  - readline 是**动态**包的平台——无静态顺序问题，`tputs` 由 .so 自己带；
  - 上游有 `--with-readline=DIR` 之类显式开关的项目（如 lftp）——那种优先用
    开关传目录，比依赖 PATH/聚合搜索更确定。
