# E-DRAFT: 2016 年前旧版 autotools 源码在 OHOS 的引导修复

- **触发实例**：libfec 1.0 适配（2026-09-18，任务 libfec-1.0-r01-pc3-10，分支 feat/libfec-1.0）
- **错误签名**：`configure: error: cannot guess build type` →
  `make: gcc: No such file or directory` → `make: install: No such file or directory`
- **类别**：autotools, ohos, portability, toolchain
- **严重度**：2（确定性阻塞，修复模式固定）

## 症状

```text
./configure --prefix=...
configure: error: cannot guess build type; you must specify one
make: gcc: No such file or directory
make: install: No such file or directory
make: ldconfig: No such file or directory
```

## 根因

1. **config.guess/config.sub 版本过旧（2016 年）**：既无 HarmonyOS 检测分支，也缺少
   patch-autotools-ohos.pl 依赖的 `__ANDROID__`/`android-linux`/`linux-uclibc` 锚点。
   直接打补丁报 `Could not find __ANDROID__`；config.sub 不认 `aarch64-linux-ohos` 三元组。
2. **OHOS 工具链缺失命令**：无 gcc（仅 clang）、无 coreutils `install`、无 `ldconfig`（toybox）。
   上游 makefile.in 硬编码这些命令时各阶段直接失败。

## 解决方案（实测 6 补丁）

1. 整体替换 config.guess/config.sub 为 2023-08-22 版（仓库内 babeltrace 归档
   `archives/b/babeltrace/1.5.11/patches/autotools/config/` 有副本），chmod +x 后运行
   `perl scripts/patch-autotools-ohos.pl config.guess config.sub`，5/5 校验通过：
   `./config.guess` → `aarch64-unknown-linux-ohos`。
2. makefile.in `gcc` → `$(CC)`（clang）。
3. install 规则 `install -m` → `cp -f`，加 `$(DESTDIR)` 前缀与 `$(srcdir)/` 源文件前缀。
4. configure.in 对 `linux-ohos*|ohos*` 平台 REBIND（ldconfig）置空。

## 适用边界 / 反例

- 适用于 config.guess 旧于 2018（无 __ANDROID__ 锚点）的 autotools 库；新版本可直接打补丁（E007）。
- 反例：显式 `--build/--host` 绕过（E007 forbid）会误判交叉编译、跳过 AC_RUN_IFELSE。

## 验证

```text
./config.guess          → aarch64-unknown-linux-ohos
./config.sub aarch64-linux-ohos → aarch64-unknown-linux-ohos
./configure --prefix=... && make && make test  →  8/8 上游用例通过
```
