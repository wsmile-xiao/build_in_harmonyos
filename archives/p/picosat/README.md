# PicoSAT

> 带证明与不可满足核支持的 SAT 求解器。

## 简介

PicoSAT 是 Johannes Kepler University（Armin Biere）的命题可满足性（SAT）
求解器，输入 DIMACS CNF，支持增量求解、证明与 core 提取。965 版 API 为
可重入式（`PICOSAT_REENTRANT_API`，`PICOSAT_API_VERSION 953`），核心入口为
`picosat_init/picosat_add/picosat_sat/picosat_deref/picosat_reset`。

库由 `picosat.c + version.c` 打包为 `libpicosat.a`，头文件仅 `picosat.h`；
同时可构建 `picosat/picomcs/picomus/picogcnf` 四个命令行工具。

## OHOS 适配要点

- 上游是 custom `configure.sh + makefile.in`，非 autotools：一律
  `sh ./configure.sh` + `make -j1 CC from Conan conf`，不依赖 `/bin/sh`。
- 生成的 `makefile` 用 `./mkconfig.sh` 产生 `config.h`；适配在构建时改写为
  `sh ./mkconfig.sh`，无源码补丁。
- 上游 965 无 `tests/` 目录、无 `check/test` target，判 `no_tests`；
  消费者测试直接调库 API 验证 SAT/UNSAT 两条路径。
- 本适配只装包库与头文件，四个 CLI 仅参与构建验证，未建 `commands.json`。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| 无 | - | 纯 C，仅需 libc |

## 功能验证

```bash
clang test_picosat.c -o test_picosat -lpicosat && ./test_picosat
```

## 参考

- [官方主页](https://fmv.jku.at/picosat/)
- [源码包](https://fmv.jku.at/picosat/picosat-965.tar.gz)
- [Debian 源码一览](https://sources.debian.org/src/picosat/965-2/)
