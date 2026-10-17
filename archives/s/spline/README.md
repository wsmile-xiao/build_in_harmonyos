# spline

`spline` 提供 `aspline(1)`：从若干 `(x, y)` 数据点（文件或 stdin）拟合
**Akima 样条**，输出**近似等间距**的插值点，且输出集**包含原始输入点**。

Akima 样条相比普通三次样条的优势是**不会在数据点之间产生多余的摆动**
（overshoot），更接近手绘曲线；代价是二阶导数不连续。数据集之间用空行分隔。

## Versions

| Version | Status | Assertions |
| --- | --- | --- |
| 1.2 | built | 51 |

Homepage: https://tracker.debian.org/pkg/spline

## 用法

```
aspline [-hv][-a [xstep]][-l llimit][-u ulimit][-n points] {data-file(s)}

  -a, --auto      supply abscissas automatically.
  -l, --llimit    set lower x-limit.
  -u, --ulimit    set upper x-limit.
  -n, --points    space output points so that approx. n intervals
                  occur between the lower and upper limit.
  -h, --help      display this help and exit.
  -v, --verbose   be verbose.
  -V, --version   display version and copyright information and exit.
  -W, --warranty  display licensing terms.
```

```bash
# 由 5 个点拟合，输出默认 101 个点（100 个区间）
printf '0 0\n1 1\n2 4\n3 9\n4 16\n' | aspline

# 只给 y 值，abscissa 自动按 1 递增
printf '1\n3\n5\n7\n' | aspline -a 1

# 只要 20 个区间
aspline -n 20 data.txt

# 限制输出区间
aspline -l 0.5 -u 2.5 data.txt
```

数据集之间用**空行分隔**；多个文件参数会被分别处理。

## 实测行为（OHOS aarch64）

| 情形 | 行为 |
| --- | --- |
| 默认（5 点，x 0..4） | 输出 **101 行**（100 个区间），前三点等间距 0.04 |
| 常量输入 y=c | 输出**每一行仍为 c**（常量保持性） |
| 输入点 | **全部出现在输出中**（含首末 `(0,0)` 与 `(4,16)`） |
| 输入 x 递减（3,2,1） | 输出被**升序整理**（首点 x=1） |
| `-n 20` | 输出 21 行（20 个区间） |
| `-n` 较小且输入点较多 | 行数被**输入点数托底**，**不随 n 单调**（`-n 3`→7 行、`-n 4`→5 行） |
| 空输入 | 无输出，退出码 0 |
| 单点 | 原样输出该点 |
| 非数字输入 | `<file>:<行号>: parse error at '...'` |
| 打开不存在的文件 | `aspline: can't open "…": No such file or directory.` |
| `-a` 缺参数 | `option requires an argument: a` + 用法块（**退出码仍为 0**，上游未把它当错误） |

> ⚠ **用法行与版本串里的程序名取自 `argv[0]` 的 basename**：把二进制复制成别的
> 名字再调用，输出里的名字会跟着变（本包测试因此只断言与程序名无关的部分）。

## OHOS 适配

| 项目 | 说明 |
| --- | --- |
| 目标 | `aarch64-linux-ohos`（musl）|
| 源码 | 两个 `.c`（`aspline.c` + `utils.c`）+ `utils.h` |
| 外部库 | 无（仅 `libc` + `libm`）|
| patch | 无 |
| 构建 | 直驱 clang：`clang -O2 -w -std=gnu99 -D_GNU_SOURCE -DHAVE_GETLINE -DVERSION=\"1.2\" -o aspline aspline.c utils.c -lm` |
| 产物 | `bin/aspline`（约 35 KB）；`share/man/man1/aspline.1`、`share/doc/spline/{README,CREDITS}` |

### 为什么不用上游 Makefile

上游 `Makefile` 的 `CFLAGS` 含 **`-mfpmath=sse`（x86 专有）** 以及一长串 GCC 告警
开关，在 aarch64 + clang 下无法使用。直编时需补上它 `DEFS` 里的三个宏
（`_GNU_SOURCE`、`HAVE_GETLINE`、版本宏），否则 `getline` 未声明、版本串为空。

## 测试

上游**不含任何测试套件**：`Makefile` 只有 `all` / `clean` / `install` 类目标，
**没有 `check` 或 `test` 目标**，源码 tarball 内也无测试源文件或期望输出。

`test_package/test_spline.c` 提供 **51 条断言**，判据主体是**自闭合属性**而非
golden 向量：

| 编号 | 属性 | 说明 |
| --- | --- | --- |
| **P1** | **输入点包含性** | 手册明示 "includes the input set" —— 逐点校验 y=x² 的 5 个输入点都出现在输出中 |
| **P2** | **常量保持性** | 输入全为常量 y=c 时，输出全部 101 行必须仍为 c（实测 5 / 0 / -3.25 三个常量） |

外加结构性属性与错误路径：

- 输出 **x 严格递增**、行数不少于输入点数、首末 x/y 与输入端点一致
- 默认 **101 行**（100 个区间）、前三点等间距 0.04
- `-n` 各档退出码 0、行数落在 **[输入点数, 2n+2]** 内（**不断言单调性**——实测非单调）
- `-a 1` 自动 abscissa、`-a` 缺参报错；递减输入被升序整理
- `-h`/`--help`/`-V`/`--version`/`-W` 与错误路径（空输入、单点、非数字、不存在文件）

判据全程用 `popen` 内存管道直读；输入数据集写到 `test()` 阶段创建于
`build_folder` 下的 scratch 目录（OHOS 上 `/tmp` 只读），并显式探测可写性。
