# E721 — OHOS musl 的 `<dirent.h>` 不传递 `<limits.h>`：`NAME_MAX` 未声明

## 错误特征

```
a/direntdup.c:32:37: error: use of undeclared identifier 'NAME_MAX'
  if (ROUND_UP (DIRENT_D_NAME_OFF + NAME_MAX, DIRENT_ALIGN) < DIRENT_SIZE)
                                    ^
```

伴生（同一源码包的配置阶段）：

```
Invalid configuration `aarch64-linux-ohos': system `ohos' not recognized
Invalid configuration `aarch64-unknown-linux-ohos': machine `aarch64-unknown-linux' not recognized
```

## 触发条件
- 构建系统：autotools（随包分发的 2016 年 config.sub）
- 阶段：compilation（`NAME_MAX`）；configuration（旧 config.sub）
- 实例：lfanew 20230825（gitlab.com/tkchia/lfanew），`a/direntdup.c` 只 include
  `<stddef.h> <stdlib.h> <string.h> <lfanew/dirent.h>`（后者只含 `<dirent.h>`）

## 根因分析

POSIX 规定 `NAME_MAX` 在 `<limits.h>`。glibc 的 `<dirent.h>` 会经内部头间接带出它，
所以上游在 glibc / MinGW 上一直编得过；OHOS SDK 的 musl `<dirent.h>` 只包含
`features.h`、`bits/alltypes.h`、`bits/dirent.h`，`NAME_MAX` 只在 `<limits.h>` 定义，
没有显式 include 就是未声明标识符。

与 `E543-draft-2EE3`（zpl.h 中 `PATH_MAX`）同属「musl 无传递包含」族，本条补
`<dirent.h>` → `NAME_MAX` 这条签名（引擎此前把该报错误配到 E493 `program_invocation_name`）。

## 解决方案

### 推荐方案
在使用 `NAME_MAX` 的源文件中无条件补 `#include <limits.h>`（一行 portability 补丁，
`refresh-patch --auto` 生成）。对所有 POSIX 平台都正确，可回馈上游。

### 伴生：旧 config.sub 不认 OHOS 三元组
若 `configure.ac` 没有 `AC_RUN_IFELSE`/`AC_TRY_RUN` 一类运行期探测，可不改 config.sub，
在配方 `generate()` 里：

```python
if self.settings.os == "OHOS":
    tc.update_configure_args({"--host": "aarch64-unknown-linux-musl"})
```

（OHOS libc 就是 musl，旧 config.sub 认识该三元组。）
同代 config.guess 也不认 `uname -s = HarmonyOS`：在 HarmonyOS 原生构建机（CI）上会报 `cannot guess build type`，必须同时加

```python
if self.settings_build.os == "OHOS":
    tc.update_configure_args({"--build": "aarch64-unknown-linux-musl"})
```

build == host，configure 仍按原生构建（`whether we are cross compiling... no`）。只传 `--host` 在 x86 runner 上能过，上 CI 必红（lfanew PR #13081 首轮）。有运行期探测时仍按 E122 / E564 系给 config.sub 打补丁。

### 禁止做法
- ❌ `-DNAME_MAX=255` 或在源码里 `#define NAME_MAX 255`：与 `<limits.h>` 冲突，掩盖缺失的标准头
- ❌ 用 `#ifdef __OHOS__` 包 include：缺的是标准头不是平台差异，违反 R8 且会被 PF5 拦截

## 验证

```bash
grep -n "include" $SYSROOT/usr/include/dirent.h        # 无 limits.h
grep -n "NAME_MAX" $SYSROOT/usr/include/limits.h       # 定义在此
conan create archives/l/lfanew/0-20230825 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# test_package: lfanew consumer test: 39/39 checks passed（含 scandir + _direntdup）
```

## 关联条目
- 相似：E543（draft 2EE3，PATH_MAX 无传递包含）
- 相关：E122 / E564（config.sub 不认 ohos 的补丁路线）、E544（静态 CLI 经 qemu 实跑）
