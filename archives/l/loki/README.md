# loki

## 简介
Loki 是对**一般家系**做多维性状连锁分析（MCMC / 吉布斯抽样）的 C 程序
（Simon Heath，2003–2004）。本包安装四个命令行程序：

- `loki`：主分析程序（读参数文件，输出连锁/关联统计）
- `prep`：数据预处理（读控制文件，生成 loki 所需 `.dat/.gen/.nrm/.opt`）
- `qavg`：数值列均值/方差统计
- `hist`：数值直方图

- 上游: https://www.stat.washington.edu/thompson/Genepi/loki.shtml
- 许可证: GPL-2.0-or-later
- 平台: OpenHarmony PC (aarch64-linux-ohos), clang 15
- 构建: autotools（上游自带已生成 configure）；无外部库依赖

## OHOS 适配

- **`-fcommon`**：2003 年代 C 依赖 gcc 默认的 tentative definitions；clang 15 默认
  `-fno-common`，会让 `loki`/`prep` 链接期报 `duplicate symbol`（E491）。
- **`umask 077`**：`configure`/`config.status` 在 HMDFS 上无法建临时文件（E011/E528），
  配方改写为 `umask 022`。
- **`AR`/`RANLIB`**：OHOS 只装 `llvm-ar`/`llvm-ranlib`，configure 探测的 GNU 名不可用（E012）。
- 上游随包预生成 flex/bison 源，无需 bison/flex。

## 测试

上游 `test/` 提供 `make tests`（7 个统计回归），配方在 `build()` 内实跑并断言 **7/7**；
`test_package` 另做 **11** 项消费者断言（四程序可执行、版本/用法、合成数据上的
`hist`/`qavg` 真实计算）。

## 构建与验证

```sh
conan create archives/l/loki/2.4.7.4 \
  -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing --user=ohpcd --channel=stable
```

## 参考

- [Debian 源包](https://sources.debian.org/src/loki/2.4.7.4-12/)
