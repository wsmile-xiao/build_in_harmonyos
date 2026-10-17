# E429（草稿 5ED1）— ohpcd ncurses/6.6 以 root 运行时忽略 TERMINFO：本地 qemu 实跑 ncurses TUI 报 cannot initialize terminal type

- **条目**：`knowledge/drafts/E429-draft-5ED1.kv`
- **来源软件**：shed 1.16（ncurses 十六进制编辑器，依赖 `ncurses/6.6`）
- **日期**：2026-09-28

## 错误特征

x86 runner 上按 E544 路线（同源 `.o` 静态重链 + `qemu-aarch64`）实跑 ncurses TUI 的 pty 消费者测试，
`TERM=vt100`、`TERMINFO` 指向 ncurses 包内（可读）的 terminfo，程序仍立即退出：

```
ncurses: cannot initialize terminal type ($TERM="vt100"); exiting
```

同样的二进制、同样的 terminfo 数据：

| 运行身份 | 结果 |
|---|---|
| root，继承环境 | 失败（cannot initialize terminal type） |
| root，terminfo 复制成 root 自有副本 | 失败 |
| root，`env -i` 干净环境 | 失败（消费者用例 1/5，仅不进 curses 的 CLI 用例通过） |
| `setpriv --reuid=nobody` | 消费者 5/5、鸿蒙特有 2/2 全部通过 |

## 触发条件

- 被测程序静态链接 ohpcd 的 `ncurses/6.6`（`libncursesw.a`）；
- 进程 uid/euid 为 0（x86 runner 的默认身份），或 `issetugid()` 为真；
- 运行机上不存在编译期默认 terminfo 目录 `//share/terminfo`（ncurses 以 `--prefix=/` 构建）。

## 根因分析

ncurses 6.6 `configure`（约 10234–10318 行）：

1. 先探测 "conventional multiuser system"：`/etc/passwd` 中删掉 shell 为 true/false/nologin/空、uid 为 1～2 位数的行后，
   若还有剩余行则 `cf_cv_multiuser=yes`，否则 `no`；
2. **只有** `cf_cv_multiuser=yes` 时才处理 `--enable-root-environ` / `--enable-setuid-environ`（默认都是 yes，
   定义 `USE_ROOT_ENVIRON` / `USE_SETUID_ENVIRON`）；为 `no` 时两个宏都不定义，显式传参也只会得到
   "ignoring options used only for multiuser systems"。

`include/nc_access.h`：两个宏都定义时 `use_terminfo_vars()` 恒为 1，否则为 `_nc_env_access()`；
`ncurses/tinfo/access.c` 中 `_nc_env_access()` 在 `issetugid()` 或 `getuid()/geteuid() == 0` 时返回 FALSE。
`ncurses/tinfo/db_iterator.c` 只在 `use_terminfo_vars()` 为真时读取 `TERMINFO`、`$HOME/.terminfo`、`TERMINFO_DIRS`，
否则只剩编译期目录——即 `//share/terminfo`，运行机上不存在，`initscr()` 失败。

ohpcd 包的证据（`_nc_env_access` 本身在 `access.o` 里无条件定义，它的存在不说明问题；有说服力的是调用方与条件编译段）：

```
# 其它目标文件对 _nc_env_access 的外部引用
$ llvm-nm -A <ncurses>/lib/libncursesw.a | grep ' U _nc_env_access'
（comp_error.o、db_iterator.o、home_terminfo.o、write_entry.o 各 1 处，共 4 处）
# 其中 db_iterator.o、home_terminfo.o、write_entry.o 三处来自 use_terminfo_vars()：USE_ROOT_ENVIRON 与
# USE_SETUID_ENVIRON 都定义时它是常量 1，这三处引用就不会存在；comp_error.o 的一处是 --with-trace 下
# `if (_nc_env_access()) abort();` 的直接调用（comp_error.c 第 158 行），与开关无关，不计入证据

# 仅在 USE_ROOT_ACCESS 未定义时才编译的两个函数确实存在
$ llvm-ar x <ncurses>/lib/libncursesw.a access.o && llvm-nm access.o | grep -E ' T _nc_safe_(fopen|open3)'
0000000000000290 T _nc_safe_fopen
000000000000032c T _nc_safe_open3
```

结论（据此推断，未取得该次构建的 config.log）：ohpcd 构建 ncurses 时 configure 把系统判为非多用户系统，
三个 root/setuid 开关都没有生效，root 身份下 terminfo 相关环境变量全部失效；实测现象（root 失败、nobody 通过）与之一致。
CI worker 若以非 root 运行（uid 未直接核实），`TERMINFO` 由 ncurses 的 runenv 经 `conanrun` 注入，不受影响；
受影响的是 x86 runner 上以 root 做的本地实跑（以及设备上以 root 运行 TUI 的场景）。

## 解决方案

### 推荐方案：本地实跑降权为非 root

```bash
D=<scratch>
cp -r <ncurses>/share/terminfo $D/terminfo
cp <static app> <static tests> $D/
chmod -R a+rX $D && chmod 777 $D
setpriv --reuid=nobody --regid=nogroup --clear-groups \
    env HOME=$D TERMINFO=$D/terminfo ./test_prog $D/app $D/work
```

配方与 test_package 无需为此改动。

### 回退方案（仅 ncurses 配方维护者）

确需 root 使用 `TERMINFO` 时，在 ncurses 的 configure 前预置 `cf_cv_multiuser=yes`，让默认的 root/setuid environ
开关生效；只传 `--enable-root-environ` 无效。下游配方不得修改依赖包。

无法降权时，应把 root 下的失败如实记为「本地未实跑」或带明确说明的条件跳过（DRAFT-12001 中 tmatrix 1.4 的
测试就是这样处理的），不得写成通过。

### 禁止做法

- ❌ 把它当成 terminfo 缺失/路径错误去改被测包配方，或把 terminfo 复制进 `/share/terminfo` 等系统路径（污染共享构建机）；
- ❌ 把 root 下的失败静默改成 skip，或在 notes/PR 里写成已通过。

## 验证

```bash
# 1) 确认 ncurses 编入了 root 限制（use_terminfo_vars() 未被展开成常量 1）：
#    db_iterator.o / home_terminfo.o / write_entry.o 三处引用有效，comp_error.o 那处是直接调用，不计
llvm-nm -A <ncurses>/lib/libncursesw.a | grep ' U _nc_env_access'
# 2) root 复现
env -i TERM=vt100 TERMINFO=<readable terminfo> ./tui-static        # cannot initialize terminal type
# 3) 降权后恢复
setpriv --reuid=nobody --regid=nogroup --clear-groups env TERM=vt100 TERMINFO=<readable copy> ./tui-static
```

shed 1.16 实测（本地证据：`archives/s/shed/1.16/notes.md`「本地实跑」一节）：root 下消费者用例 1/5（4 个进入 curses
的用例全部 cannot initialize terminal type），nobody 下消费者 5/5、鸿蒙特有 2/2 通过。

## 查重

查重时点：2026-10-01，对 `origin/main`（`d66b727118`）重新核对；初次查重在 2026-09-28。

- **`DRAFT-12001-runenv-terminfo-shadows-ncurses`（2026-09-30 随 tmatrix 1.4 合入）——部分重叠，须一并处理**：
  它的主题是「应用包重新声明依赖已导出的 `TERMINFO` 会覆盖依赖的正确值」（runenv 后写者胜出），与本条不同；
  但其「Related, but a separate trap」旁注已独立观察到本条的核心现象——已发布的 ncurses/6.6 未定义
  `USE_ROOT_ENVIRON`，`use_terminfo_vars()` 落到 `_nc_env_access()`，`euid == 0` 时返回假，root 下
  `cannot initialize terminal type`，非特权 uid 下正常。两处在这一事实上**相互印证**（两个不同的包、不同的测试），
  本条**不是**该现象的首次记录。本条的增量：①成因链——configure 的 `cf_cv_multiuser` 探测、三个开关的联动、
  `--enable-root-environ` 在非多用户系统上被忽略，附 ncurses 源码位置；②库内证据——`libncursesw.a` 中经
  `use_terminfo_vars()` 引用 `_nc_env_access` 的三个目标文件与条件编译的 `_nc_safe_fopen`，并说明哪一处引用不能当证据；
  ③可执行的本地处置——x86 runner 上降权为非 root 后完整实跑（消费者 5/5、鸿蒙特有 2/2，root 下 1/5），而不是只能条件跳过；
  ④ncurses 配方侧的回退方案（预置 `cf_cv_multiuser=yes`）。建议主编 promote 时把两处的 root 侧结论归并到同一条。
- `DRAFT-E568-mdp-ohos-musl-terminfo-path`：同一报错，根因是 terminfo 搜索路径未导出，修法是 export `TERMINFO`——
  本条中 `TERMINFO` 已正确导出，按其修法无效；
- `DRAFT-pty-driven-interactive-test-traps`：pty 测试时序/断言陷阱，提到 terminfo 不可读会报同一错误，未涉及 uid；
- 正式库 `index.tsv`（542 条）中 `cannot initialize terminal` / `root-environ` / `_nc_env_access` / `cf_cv_multiuser` 均 0 命中；
  `draft-review` 判 `create`——注意该工具只比对正式库，不比对其它草稿，上面三条草稿间的重叠是人工扫描
  `knowledge/drafts/`（2722 个 `.kv`）得到的。

## 关联条目

- E544（草稿族）：x86 runner 无法运行 OHOS 动态产物 → 同源 `.o` 静态重链 + qemu；本条是该路线跑 ncurses TUI 时的前置条件。
- `DRAFT-12001-runenv-terminfo-shadows-ncurses`：同一依赖（ncurses/6.6）上的 `TERMINFO` 导出问题；本条的降权处置与其旁注互补。
