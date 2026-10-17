# spigot

**精确实数计算器** —— Simon Tatham 的 *exact real calculator*。

给一个数学表达式，spigot 按任意精度**逐位**把结果算出来（spigot 算法），
默认一直往标准输出打数字，直到你按 Ctrl-C。

> ⚠️ 名字容易误解：这里的 spigot 是 Simon Tatham 写的计算器，
> **不是** Minecraft 的 Spigot 服务端。

## 特性

- 任意精度：`spigot -d100 pi` 输出 π 的 100 位小数
- 巨大的内置函数库：三角/反三角/双曲、Gamma/Lanczos、Bessel、Lambert W、
  Zeta、Hurwitz、指数/对数积分 `Ei`/`E1`/`li`/`Li`、Fresnel、
  `erf`/`erfc`/`Phi` 及其反函数、`algebraic()` 代数数求解器 …
- **精确算术**：结果位数不够时不会瞎编，而是继续算下去
- 任意进制输出：`-b2` / `-b16` / `-B36` / `-b60`
- 输出格式：`--printf=%a` / `%e` / `%f` / `%g`，可带宽度与标志位
- 连分数输出 `-c`、有理数输出 `-R`
- 文件字面量：`baseNfile:` / `cfracfile:` / `baseNfd:` / `cfracfd:`
- 大数后端可切到 **GMP**（`spigot --version` 会报 `big integer provider: gmp`）
- 交互式行编辑（ncurses）

## 用法

```console
$ spigot -d20 pi
3.14159265358979323846
$ spigot -d20 'sin(1/3)'
0.32719469679615224420
$ spigot -d10 --printf=%e 'pi^12'
9.242692e+05
$ spigot -b16 -d40 pi
3.243f6a8885a308d313198a2e03707344a4093822
$ spigot -R 'sqrt(16)'
4
$ spigot --version
spigot, 0.2017-01-15.gdad1bbc6
  big integer provider: gmp
  fd literals (cfracfd:F, baseNfd:F): supported
```

不接参数直接运行 `spigot` 会进入交互模式，逐个读表达式、输出数字。

## 本仓库适配说明

- 版本：`0.2017-01-15.gdad1bbc6`（上游 commit
  `dad1bbc6f8fbb588a7a880096d6d3610a29c064f`，2017-01-15）
- 目标平台：HarmonyOS PC / OHOS `aarch64`
- 依赖：`gmp/6.3.0`（大整数后端）、`ncurses/6.6`（行编辑），
  构建期 `halibut/1.3`（生成 man page 与 HTML 文档）
- 源码零改动，无补丁
- 上游自带 1133 个 testcase 的测试套件在构建阶段全量执行（1133 pass / 0 fail）
细节见 `0.2017-01-15.gdad1bbc6/notes.md`。

## 上游

- 主页：<http://www.chiark.greenend.org.uk/~sgtatham/spigot/>
- 源码：<https://git.tartarus.org/simon/spigot.git>
- 许可证：MIT（Copyright 2007-2016 Simon Tatham）
