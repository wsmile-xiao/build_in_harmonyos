# slgsl 0.10.0-pre.7 — OpenHarmony PC 适配笔记

## 概览

| 项 | 值 |
|---|---|
| 包名 | slgsl |
| 版本 | 0.10.0-pre.7（上游 tar 名 `slgsl-pre0.10.0-7`） |
| 上游 | S-Lang GSL modules（MIT，作者 John E. Davis；主页 space.mit.edu/cxc/...） |
| 源码 | `https://jedsoft.org/snapshots/slgsl-pre0.10.0-7.tar.gz` |
| sha256 | `11963a7343c44400984b0e55f1b3b960e2e4c08e6c1efa81245a44091ef04788` |
| 构建系统 | autotools（configure + make，**强制源码内构建**） |
| 依赖 | `slang/2.3.3`（宿主 + `slsh` 解释器）、`gsl/2.8` |
| 产物 | `lib/slang/v2/modules/*-module.so` + `share/slsh/local-packages/*.sl` |

## 软件简介

slgsl 把 GNU Scientific Library（GSL）以**可动态加载模块**的形式暴露给
S-Lang 解释器。模块家族包括：`gslcore`（公共支撑）、`gslsf`（约 200 个
特殊函数）、`gslconst`（物理常数）、`gslinterp`（插值）、`gslrand`
（随机数与分布）、`gslcdf`（累积分布）、`gslfft`（FFT）、`gslinteg`
（数值积分）、`gsldwt`（小波）、`gslmatrix`（矩阵）等。任何支持 S-Lang
模块的应用（`slsh`、`jed`、`slrn`、`isis`）都可加载。

## 构建要点（4 个坑，均已修）

### 1. 设备 `uname -s` 返回 **HarmonyOS**（不是 Linux）

2018 版 `config.guess` 只认 `Linux|GNU|GNU/*`，遇到 `HarmonyOS` 会落到
"unable to guess"。**注意**：不能只是把 `HarmonyOS` 加进那个 case ——
该分支会**编译一段 dummy.c 探针**（检测 glibc 类型），而设备上
`/tmp` 只读、`mktemp -d` 受 umask 限制，探针必然失败。正确做法是**直接
判定并输出三元组后 exit**（补丁 0001）：

```sh
HarmonyOS)
    case "$UNAME_MACHINE" in
        aarch64|arm64) GUESS=aarch64-unknown-linux-ohos ;;
        *)             GUESS="$UNAME_MACHINE-unknown-linux-ohos" ;;
    esac
    echo "$GUESS"
    exit ;;
Linux|GNU|GNU/*)
```

### 2. 旧版 `config.sub` 需**三处齐改**

漏任一处都会得到错误的系统串：

| # | 位置 | 作用 |
|---|------|------|
| 1 | `maybe_os` 列表加 `linux-ohos*` | 让 `aarch64-unknown-linux-ohos` 被识别为 KERNEL-OS |
| 2 | OS 合法性列表加 `-linux-ohos*` | 避免被判为非法系统 |
| 3 | 在 `-linux*)` **之前**加 `-linux-ohos*) os=-linux-ohos ;;` | 否则被通用规则改写成 **`linux-gnu-ohos`** |

实测修复前：`config.sub aarch64-unknown-linux-ohos` → `aarch64-unknown-linux-gnu-ohos`；
修复后 → `aarch64-unknown-linux-ohos`。

### 3. `configure` 的 `umask 077` 临时目录（hmdfs 坑）

`config.status` 用 `(umask 077 && mktemp -d "./confXXXXXX")` 建临时目录；
在 hmdfs 上该目录**属主为本会话却不可写**（且 chmod 是空操作），于是：

```
./config.status: line 603: ./confbtQOpl/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

改为 `umask 022`（补丁 0002，SDL / inn2 同款修法）。

### 4. 必须源码内构建

上游 `configure` 有显式检查：

```sh
cd $srcdir
if test "`pwd`" != "$CONFIG_DIR"; then
  as_fn_error ... "This software does not support configuring from another directory."
fi
```

故配方 `layout()` 里 `self.folders.build = "."`（SDL 先例）。

## 上游测试与 slsh 环境（R51）

上游 `src/Makefile` 的 `check` 目标遍历 `src/tests/test_*.sl` 并用 `slsh`
执行（6 个测试：import / err / fft / interp / integ / rand）；配方在
`build()` 内真实运行 `make check`。

**关键**：测试脚本首行调用 `prepend_to_slang_load_path()`，该函数**仅由
slang 包的 `etc/slsh.rc` 定义**。`slsh` 通过 `SLSH_CONF_DIR` 找 `slsh.rc`，
而 `slsh.rc` 自身又读 `SLSH_PATH`（其内容为 `prepend_to_slang_load_path
(getenv(SLSH_PATH_ENV))`）。缺任一都会得到：

```
prepend_to_slang_load_path is undefined
...:Undefined Name
```

配方 `_env()` 为此同时设置：

```
SLSH_CONF_DIR = <slang>/etc
SLSH_PATH     = <slang>/share/slsh  (+ 本包 local-packages)
SLANG_MODULE_PATH = <本包>/lib/slang/v2/modules    # 编译模块的 dlopen 路径
```

## test_package 设计（消费者视角）

`test_slgsl.py` 用 **已打包的 `slsh`** 加载**已打包的 gsl 模块**（真实
dlopen），执行：

| # | 断言 | 证明什么 |
|---|---|---|
| 1 | `rng_alloc` + `ran_ugaussian(r, 1000)`，样本均值 \|mean\| ≤ 0.2 | gslrand 模块真实可用、随机数分布正确 |
| 2 | `CONST_MKSA_SPEED_OF_LIGHT` ∈ [2.9e8, 3.1e8] | gslconst 模块真实可用 |

实测输出：`sample mean 0.017475 over 1000 draws` / `c = 2.99792e+08 m/s`
→ `SLGSL-CONSUMER-OK`。

## 已知平台限制

- 无 gfortran 无关（本包纯 C）。
- 运行期需 `SLANG_MODULE_PATH` + `SLSH_PATH`/`SLSH_CONF_DIR`（`package_info()`
  已为消费者铺好前两者与 `LD_LIBRARY_PATH`）。
- `-linux-ohos` 三元组需靠补丁注入；上游快照的 autotools 脚本较旧。
