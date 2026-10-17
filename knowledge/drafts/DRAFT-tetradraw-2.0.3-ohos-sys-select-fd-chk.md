# DRAFT-tetradraw-2.0.3-ohos-sys-select-fd-chk

> Draft（待审核 promote）｜对应: `knowledge/drafts/DRAFT-tetradraw-2.0.3-ohos-sys-select-fd-chk.kv`
> 说明：该 kv 为文档式条目，本文档为其可读镜像。

---

# DRAFT-tetradraw-2.0.3: OHOS sys/select.h 把 __fd_chk 注入 FD_SET，产物"链接全绿、跑起来就死"

- 条目主题：OHOS 交叉编译出的可执行文件在任何非 OHOS-sysroot libc 上装载失败（`Error relocating ... __fd_chk: symbol not found`）的根因、定位手法与修法
- 状态：草稿（待知识库主编审核，拟提升编 Exxx）
- 关联包：tetradraw 2.0.3（ANSI 美术编辑器，ncursesw TUI，autotools）
- 关联 PR：见 tetradraw 2.0.3 积分赛 PR

## 适用场景

源码里只要出现 `FD_SET` / `FD_CLR`，交叉编译成 OHOS aarch64 之后，产物就会
引用一个 OHOS 私有 libc 符号 `__fd_chk`。编译、链接、`conan create` 全绿，
但真正执行时：

```
Error relocating /path/to/bin/foo: __fd_chk: symbol not found   # exit 127
```

典型触发面：任何用 `select()` 的 C 程序（socket 服务 / 事件循环 / 串口 /
多路复用），以及"在 WSL 交叉沙箱里跑 OHOS 二进制做 test_package 实测"的场景 ——
沙箱里那份 libc 往往不是 OHOS sysroot 那份。

## 根因

OHOS 的 `<sys/select.h>` 不是 POSIX 实现，它把 fd 越界检查内联进了宏：

```c
void __fd_chk(int fd);                       /* OHOS 私有，非标准符号 */
#define FD_SET(d, s) do { __fd_chk(d); \
        ((s)->fds_bits[(d)/(8*sizeof(long))] |= (1UL<<((d)%(8*sizeof(long))))); } while (0)
#define FD_CLR(d, s) do { __fd_chk(d); ... } while (0)
```

`__fd_chk` 只由 OHOS sysroot 自带的 `libc.so` 导出（实测：
`nm -D <ohos-sysroot>/usr/lib/aarch64-linux-ohos/libc.so | grep __fd_chk` 命中）。
换任何别的 libc 装载就必然缺符号，而链接期**完全不给警告**（静态库/共享库都
不校验这个私有符号的可见性）。

⚠️ **重要反直觉点：这不是 `_FORTIFY_SOURCE` 造成的。** 第一次排查时很自然会
想到 FORTIFY，于是加 `-U_FORTIFY_SOURCE` 重编 —— `__fd_chk` 一个不少地还在。
因为 FORTIFY 改写的是 `fopen`→`__fopen_chk` 这类 *stdio* 调用，而 `__fd_chk`
是平台头文件无条件注入的 `FD_SET` 宏。**先确认符号来自哪个头文件，再决定开关。**

## 诊断步骤

1. 现象是 exit 127 + `Error relocating ...: <sym>: symbol not found`，先 `nm -u <binary> | grep -i chk` 拿到符号名。
2. 逐个 `.o` 回溯引用者，别只看最终二进制：
   `for o in $(find <build_dir> -name '*.o'); do nm -u "$o" | grep -q <sym> && echo "$o"; done`
3. 到引用者源码里找触发点。本例是 `network.c` 的两处 `FD_SET(STDIN/remote, &fds_read)`。
4. 在 sysroot 头文件里 grep 该符号，确认是宏注入而非 libc 函数调用：
   `grep -rn "__fd_chk" <ohos-sysroot>/usr/include/`
5. 交叉确认导出面：`nm -D <ohos-sysroot>/usr/lib/aarch64-linux-ohos/libc.so | grep __fd_chk`（命中=平台私有符号）、`nm -D <交叉沙箱>/lib/libc.so | grep __fd_chk`（不命中=沙箱 libc 不是 OHOS 那份）。

## 处置

- **首选：源头去掉平台注入**。在 include 之后把宏还原成经典 POSIX 位运算：

  ```c
  #ifdef FD_SET
  #undef FD_SET
  #endif
  #define FD_SET(d, s) do { (s)->fds_bits[(d)/(8*sizeof(long))] |= \
                                    1UL<<((d)%(8*sizeof(long))); } while (0)
  ```

  代价评估：OHOS 那句检查是"fd >= 1024 就 abort"。若监控的 fd 只可能是
  STDIN / 已 accept 的 socket / 已打开的串口 fd（实践中恒 < 1024），去掉它
  不损失任何安全性，换来产物只依赖标准 `select()` ABI —— 真机 / 交叉沙箱 /
  通用容器行为一致。
- **不推荐：给 test_package 打宿主专属 LD_PRELOAD shim**（`libfdchkshim.so`
  之类）。它把"产物只能在特定 libc 上跑"这个缺陷藏进测试，还会在入库文件里
  留下机器专属路径（`/opt/...`），违反配方自包含与 R8/R49 精神。
- **兜底：确认 CI/真机用的就是 OHOS sysroot libc**，则缺陷不存在；但这条
  无法在本地证明，等于把风险推给远端车道，不作为交付前提。

## 预防

- 交叉编译的可执行文件，只要 `NEEDED libc.so` 且要在非 OHOS 环境跑，
  就把"**所有未定义符号都必须能被目标 libc 导出**"当作验收项。
- 交付前跑一次 `nm -u <每个产物> | grep -E '_chk$|__[a-z]+_chk'`，非空即中招。
- 别把 exit 127 一律当"环境问题"跳过；127 恰恰是 loader 的明确拒绝。

## 证据（真实执行）

- tetradraw 2.0.3：加 `-U_FORTIFY_SOURCE` 前，`nm -u` 有 `U __fd_chk`；
  定位到 `network.o`（`network.c` 的 `FD_SET`）；`grep -rn __fd_chk
  <sysroot>/usr/include/` 命中 `sys/select.h:33`。
- 施加还原宏的补丁 0005 后重编：`nm -u` 无任何 `*_chk` 引用，
  `conan create` RC=0，test_package **8/8 断言通过**，其中 4 条是真实执行
  两个二进制（退出码从 loader 拒绝的 127 变为正常的 ncurses 早退）。
- 本地同源门禁 `zsh ci/conan/build_and_test.sh` GATE_RC=0（L0/L1/L1e/L4/L5
  全 pass，L1e 反向破坏测试确认测试真依赖产物）。

## 推广价值

- 所有用 `select()`/`poll()` 事件循环的 C 库向鸿蒙 PC 适配
- 一切"交叉编译产物需要在本机/容器里真实执行"的适配（test_package 策略）
- 通用教训：平台头文件可以往宏里塞**只有自家 libc 才有的符号**，链接器不会报警

## 查重关键词

`__fd_chk`、`sys/select.h`、`FD_SET`、`FD_CLR`、`Error relocating`、`symbol not found`、
`exit 127`、`aarch64-linux-ohos`、`交叉执行沙箱`、`libc.so`、OHOS musl、
`_FORTIFY_SOURCE` 反直觉、tetradraw
