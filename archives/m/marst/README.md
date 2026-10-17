# marst

**GNU MARST — Algol-60 到 C 翻译器**（附带 Algol 运行库 libalgol）

marst 将 Algol-60 语言源程序翻译为可由任意 C 编译器编译的 C 代码；翻译产物与包内 `libalgol` 运行库（`algol.h`）链接即可运行。包内另含 `macvt` 工具（MARST listing 转换器）。

## 用法

```bash
marst [options] [filename]
macvt [options] [filename]
```

| 选项（marst） | 说明 |
|------|------|
| `-o filename` | 输出 C 代码到指定文件 |
| `-t` | 输出翻译统计 |
| `-w` | 关闭警告 |
| `-l nnn` | 输出行宽（默认 72） |
| `--version` / `--help` | 版本 / 帮助 |

典型流程（翻译并运行一个 Algol 程序）：

```bash
marst -t -w hello.alg -o hello.c
cc -I<prefix>/include hello.c -o hello <prefix>/lib/libalgol.a -lm
./hello
```

## 鸿蒙适配

- 构建系统：Autotools（release tarball 自带 configure）
- 关键修复：E011（configure `umask 077` 在 HMDFS 上产生不可写临时文件，已补丁改为 022）；`--build=aarch64-unknown-linux-gnu`（2007 年版 config.guess 不识别 OHOS）
- 产物：`bin/marst`、`bin/macvt`、`include/algol.h`、`lib/libalgol.a`
