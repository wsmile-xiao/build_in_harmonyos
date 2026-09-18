# 旧版 autotools 脚本 OHOS 适配：config.guess echo+exit / libtool 硬编码路径

> 草稿（DRAFT）。与同目录 `DRAFT-libpar2-0.2-old-autotools-scripts-ohos-adaptation.kv` 成对。
> 来源：libpar2 0.2 适配（本 PR），任务 libpar2-0.2-r01-pc1-39-20260916T130221Z。

## 现象

1. configure 报 `cannot guess build type; you must specify one`，config.guess
   打印 `This script, last modified 2006-02-23, has failed to recognize`：

```text
checking build system type... config.guess: line 1304: .../dummy.c: Permission denied
config.guess: unable to guess system type
configure: error: cannot guess build type; you must specify one
```

2. 打上 E007 通用补丁（patch-autotools-ohos.pl）后仍然失败：脚本对 2006 版
   config.sub 报告 `sub=0 change(s)`，config.guess 补丁只设置 `GUESS=...` 变量，
   但旧版脚本在 case 结束后**没有** GUESS 后处理，仍然落入 dummy.c 探测兜底。

3. 随包 libtool 脚本硬编码 `SED="/bin/sed"`，OHOS 上访问 `/bin/sed` 报
   Permission denied（/bin 权限边界）。

## 根因

- 2006 年版 config.guess 没有 HarmonyOS 分支，也没有 "设置 GUESS 变量 →
  脚本末尾统一输出" 的新式后处理机制。E007 的通用补丁假定新式脚本，
  因此对旧版必须**在分支内直接 echo 三元组 + exit 0**。
- 2006 年版 config.sub 缺少 aarch64 CPU 与 linux-ohos 支持，且其
  `-linux*)` 归一化分支会把 `-linux-ohos` 改写为 `-linux-gnu-ohos`，
  必须加 `-linux-ohos*)` 守卫。
- 旧版随包 libtool 把 sed 路径硬编码为 `/bin/sed`（构建机上常见），
  OHOS /bin 访问受限导致运行失败。

## 方案

**config.guess（2006 版）**——HarmonyOS 分支内直接输出并退出：

```sh
*:HarmonyOS:*:*)
    case "$UNAME_MACHINE" in
        aarch64|arm64) MACHINE=aarch64 ;;
        armv7*|armv8*) MACHINE=arm ;;
        x86_64|amd64)  MACHINE=x86_64 ;;
        i?86)         MACHINE=i686 ;;
        *)            MACHINE="$UNAME_MACHINE" ;;
    esac
    echo ${MACHINE}-unknown-linux-ohos
    exit 0
    ;;
```

**config.sub（2006 版）**五处修改：
1. KERNEL-OS 列表：`linux-gnu* |` 后加 `linux-ohos* |`
2. CPU 列表：加 `aarch64`（2006 版甚至没有 aarch64）
3. 带厂商 CPU 列表：加 `aarch64-*`
4. OS 列表：`-linux-gnu* |` 后加 `-linux-ohos* |`
5. 归一化守卫：在 `-linux*)` 前加 `-linux-ohos*)`（否则被改写为 `-linux-gnu-ohos`）

**libtool**——`SED="/bin/sed"`、`Xsed="/bin/sed ..."` 改为 `/usr/bin/sed`。

补丁通过 `conandata.yml patches:` 注册，conan create 干净构建验证。

## 验证

```bash
sh config.sub aarch64-unknown-linux-ohos   # 原样输出 aarch64-unknown-linux-ohos
sh config.guess                            # 输出 aarch64-unknown-linux-ohos
conan create archives/l/libpar2/0.2 ...    # G2 PASS
```

libpar2 0.2 实测：config.guess/config.sub 补丁后三元组正确；
conan-verify G2 干净构建通过；w3-local-ci JC/L0 全 pass。

## 适用边界 / 反例

- 适用于内置 2006 年前后 config.guess/config.sub 的 autotools 库；
  较新脚本可直接用 E007 通用补丁（patch-autotools-ohos.pl）。
- libtool 硬编码路径问题仅影响随包自带 libtool 且目标机 /bin 受限的场景。
- 反例：新式 config.guess（带 GUESS 后处理）不需要 echo+exit 补丁。

## 查重差异

- 与 E007（patch-autotools-script）：E007 方案对 2006 版 config.sub 失效
  （perl 脚本模式不匹配，0 处修改），且未覆盖"旧版无 GUESS 后处理需 echo+exit"
  边界。新增差异：老版脚本直接 echo+exit、config.sub 五处手工补丁、
  libtool SED 路径改写。
- 与 E149/E160：E149 是直接编译成功记录，E160 是 config.guess HarmonyOS
  补丁（无 2006 版边界细节）。
