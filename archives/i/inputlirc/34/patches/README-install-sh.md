# 为什么 `install(1)` 要用 shim

HarmonyOS PC 镜像没有 coreutils 的 `install(1)`（`command -v install` 无结果），
且 toybox 的 `cp` 不支持 `-m`（`cp -m 644 a b` 报 `cp: Unknown option 'm'`）。
上游 `Makefile` 的三条 install 规则都走 `$(INSTALL)`，其中两条带 `-m 644`。

`INSTALL ?= install` 是普通 `?=`，命令行可覆写 ⇒ 配方在 `package()` 里生成一个
POSIX `install-sh` 并传入 `INSTALL=<path>`。**不改上游 install 规则本身**，
因此同一配方在装有 coreutils 的 Linux CI 上行为一致。
