# E14731 草稿：被重定向的函数里 `exit`，EXIT trap 的 stdout 在 mksh/bash/zsh 下仍是 /dev/tty（只有 dash 先还原）

## 错误特征

没有任何报错，只是**取不到输出**：`cd "$(shfm)"` 拿到空串，退出时目录路径被直接打印在终端屏幕上；
测试里表现为 `cd-on-exit stdout is '', expected '<dir>\n'`。同一个脚本在 Debian 主机（`/bin/sh` 是 dash）上一切正常，
所以只在 dash 下验证会误判通过。

## 触发条件

脚本末尾是 `main "$@" >/dev/tty`（函数调用整体被重定向），`main` 里 `trap 'term_reset' EXIT INT` 并在 `exit 0` 时由
trap 向 `>&1` 输出最终结果。shfm 0.4.2 的 cd-on-exit 就是这个写法：

```sh
term_reset() { ...; printf '%s\n' "$PWD" >&1; }   # needed for cd-on-exit
trap 'term_reset' EXIT INT
...
main "$@" >/dev/tty
```

## 根因

`exit` 在被重定向的函数内执行时，EXIT trap 运行的时刻不同：dash 先撤销函数调用的重定向再执行 trap（`>&1` 是调用者的 stdout）；
mksh、bash（含 `--posix`）、zsh 在重定向仍有效时执行 trap（`>&1` 就是 `/dev/tty`）。OHOS 的 `/bin/sh`（`/system/bin/sh`）是 mksh，
hnp 提供的是 bash，二者都落在“受影响”一侧。

## 实测证据（x86_64 Debian 12，mksh 使用 Debian 的 R59 作为 OHOS `/system/bin/sh` 的同源替身，未在真机上运行）

最小复现（与 shfm 无关）：

```sh
for sh in dash bash 'bash --posix' mksh 'mksh -o posix' zsh; do
  printf '%-14s -> [' "$sh"; $sh -c 'f() { trap "echo TRAP" EXIT; exit 0; }; f >/dev/null'; echo ']'
done
# dash -> [TRAP]；bash / bash --posix / mksh / mksh -o posix / zsh -> []
# 先 `exec 3>&1`、trap 里 `echo TRAP >&3` 后，六种调用方式都输出 [TRAP]
```

shfm 0.4.2（pty 驱动：按 j、l、q，stdout 接管道，等同 `$(shfm)`）：

| 脚本 | dash | bash | bash --posix | mksh | mksh -o posix | zsh |
|---|---|---|---|---|---|---|
| 原版 | stdout=目录 | stdout 为空，目录出现在 tty | 同左 | 同左 | 同左 | 同左 |
| 打补丁（fd 3） | stdout=目录 | stdout=目录 | stdout=目录 | stdout=目录 | stdout=目录 | stdout=目录 |

## 推荐处理

在重定向之前保存调用者的 stdout：顶层 `exec 3>&1`，trap 里 `printf '%s\n' "$PWD" >&3`，
并让 `cmd_run` 起的子进程 `3>&-`（子进程不该握着 `$(...)` 的管道写端，否则长驻子进程会让捕获一直等不到 EOF）。
测试必须覆盖非 dash 的 shell：pty 驱动 `bash <脚本>`，断言**stdout** 内容，而不是只看屏幕或退出码。

## 禁止做法

- 只用 `/bin/sh`（Debian 上是 dash）验证 cd-on-exit：dash 恰好是唯一不出问题的 shell，测试会假通过。
- 在 trap 里继续写 `>&1`，并把结果当成“OHOS 上也能工作”。

## 验证

```bash
for sh in dash bash mksh zsh; do printf '%s -> [' $sh; $sh -c 'f() { trap "echo TRAP" EXIT; exit 0; }; f >/dev/null'; echo ']'; done
```

查重：`engine` 对 `/dev/tty`、`stty` 两条报错无相关命中；`knowledge/drafts` 里的 pty/TUI 测试类草稿
（`DRAFT-E5xx-tui-app-pty-test-harness`、`DRAFT-E429-cfm-termios-tui-pty-consumer-test` 等）讲的是如何用 pty 驱动 TUI，
没有覆盖“EXIT trap 在被重定向函数内的 stdout 语义因 shell 而异”。仅供主编审核后确定正式编号，不执行 promote。
