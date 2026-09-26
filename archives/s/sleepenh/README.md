# sleepenh

## 是什么

sleepenh 是增强版 `sleep`：休眠精度到微秒，并打印本次休眠的**绝对结束时间**。把上一次的输出作为下一次的起点，
shell 循环就能严格按固定间隔执行，进程启动等开销不会累计：

```sh
VAL=$(sleepenh 0)                      # 取当前时间
while true; do
    do_something
    VAL=$(sleepenh "$VAL" 12.4)        # 睡到「上次结束时间 + 12.4 s」
done
```

## 用法与退出码（sleepenh.c / sleepenh.1）

```
sleepenh [[--warp|-w] INITIALTIME] TIMETOSLEEP
```

| 情形 | 行为 | 退出码 |
|------|------|--------|
| 需要休眠 | 由 `setitimer()` + `pause()` 休眠到结束时间，打印结束时间（`%f`） | 0 |
| 结束时间已过 | 不休眠，直接打印结束时间；加 `--warp` 时结束时间折返到 `INITIALTIME + k * TIMETOSLEEP` 中不晚于当前的最后一个 | 1 |
| 无参数 | 版本与用法打印到 stderr | 10 |
| 未收到 SIGALRM | — | 11 |
| 参数不是有限数（`inf`/`nan`） | — | 12 |
| `gettimeofday()` 失败 | — | 13 |

`-h`/`--help` 打印用法，`-V`/`--version` 打印版本，退出码 0。

## OHOS 适配

- 上游 Makefile 写死 `CC = gcc`：配方把 `AutotoolsToolchain` 给出的编译器放在 make 命令行上覆盖，编译标志经上游
  `EXTRA_CFLAGS` 钩子传入（R33）。
- 版本串由 `git describe` 生成，源码归档无 `.git`：与 Debian 打包相同，在 make 命令行传 `vcsversion`。
- `patches/0001-sleepenh.c.patch`：`usage()` 引用的 glibc 扩展变量 `program_invocation_short_name` 在 OHOS musl
  头文件中没有声明、`libc.so` 也不导出（`libc.a` 虽有弱别名，只在静态链接下可用），改为在 `main()` 中从 `argv[0]`
  取 basename；无平台宏。
- 上游 `install` 目标写死 `/usr`，配方 `package()` 直接把二进制复制到 `bin/`、man 页复制到 `share/man/man1/`。
- 上游无测试套件；test_package 补全 A1-A4 产物检查 + F1-F8 功能检查（共 12 项）。

## 依赖关系

- 编译依赖：无（仅 libc）
- 运行依赖：无

## 参考资料

- 上游项目：https://codeberg.org/nsc/sleepenh
- Debian 维护仓库：https://salsa.debian.org/debian/sleepenh（源码取自其 `upstream/1.8` 标签，与上游 `1.8` 标签源码树相同）
