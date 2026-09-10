# binutils 2.46.0 HarmonyOS PC 真机验证

## 最终结果

| 项目 | 结果 |
|---|---|
| 设备 | HarmonyOS PC aarch64，HDC USB |
| Conan | 2.29.1，独立 `CONAN_HOME=final-cache39` |
| 最终任务 | `j039`，2684.96 秒，退出码 0 |
| 输入 | 46 个文件，bundle SHA256 `61f2ab642e0405787a1af1fa34e47b9e12281eb9fd1d8a93d509348fc2beec79` |
| 上游 DejaGNU | 367 驱动；3419 PASS / 35 FAIL / 0 UNRESOLVED，98.99% |
| 其他上游 | libiberty 930/930；gprof 0 discovered / 0 executed；gprofng 显式关闭 |
| 消费者 | 通用 13/13 + OHOS 原生运行 3/3 = 16/16 |
| 包 | 453 个文件，65,975,560 字节 |
| 归因检查 | 名称 35/35 机器映射；日志与对照试验证据复核后，当前适配引入项 0；退出码 0 |
| 回传 | 138 个证据文件逐项校验通过 |

完整 package reference：

```text
binutils/2.46.0#11a4a9b63a85bc14b6f4edc65fc4fdfe:6b129b068851896169fae42d399fa922d239ce8a#79f95fb4875a2b5b802d4eaec2ee7349
```

最终回传归档 SHA256：

```text
8efd26e9be91e44d4deb7eb53a4d85ebc9320dc54481f00d392936b183d7c6f3
```

## 隔离与并发约束

- 设备任务根：`/storage/Users/currentUser/binutils-hdc-20260907-2342`。
- HDC 可见别名：`/storage/media/100/local/files/Docs/binutils-hdc-20260907-2342`。
- 最终输入、输出、缓存分别是 `device-bundle-r6`、`final-build39`、`final-cache39`；
  不使用其他项目路径。
- 所有任务由专属 HiShell 窗口中的文件 broker 串行执行；没有向其他标签页输入命令。
- UI 操作前获取全局锁并错时等待，输入完成后退出 UI 操作；后续仅使用 HDC 文件队列。
- 设备会话中断的 `j036-j038` 明确记录 `rc=130`，其部分结果不参与验收。

## 可复现命令

设备端等价构建命令为：

```sh
export CONAN_HOME=/storage/Users/currentUser/binutils-hdc-20260907-2342/final-cache39
export TMPDIR=/storage/Users/currentUser/binutils-hdc-20260907-2342/final-tmp39
export CONFIG_SHELL=/data/service/hnp/bin/bash
export SHELL=$CONFIG_SHELL
export MAKEFLAGS=-j1

conan create \
  /storage/Users/currentUser/binutils-hdc-20260907-2342/device-bundle-r6/recipe \
  -tf /storage/Users/currentUser/binutils-hdc-20260907-2342/device-bundle-r6/test_package \
  -pr:h /storage/Users/currentUser/binutils-hdc-20260907-2342/device-bundle-r6/ohos-aarch64.profile \
  -pr:b /storage/Users/currentUser/binutils-hdc-20260907-2342/device-bundle-r6/ohos-aarch64.profile \
  --build=missing --build='binutils/*'
```

配方在 build 阶段执行 `make -k -j1 check`，要求五套 DejaGNU 汇总、367 个驱动、
无 ERROR/driver abort，且 `PASS/(PASS+FAIL+UNRESOLVED) > 90%`。随后执行 libiberty、
打包和 `test_package`。

## 关键真机证明

1. GNU ld 生成程序若缺平台签名返回 126；使用平台 `binary-sign-tool` 后返回 0。
2. `pr21964-2` 在 literal dlopen DSO 未签名时返回 2；只签名
   `pr21964-2b.so` 后输出 `PASS`、返回 0。最终 helper 只增加该精确映射。
3. `compress.exp` 使用 Clang integrated assembler 时产生 24 个 FAIL；仅在该驱动内
   使用本轮 GNU as 后为 28/28 PASS，并在退出驱动时恢复标志。
4. 过宽外部 as 试验新增 `mbind2a/b` 两项 FAIL，归因门禁将其判为适配缺陷；最终
   收窄版本将两项恢复为基线的 UNSUPPORTED，未形成 FAIL。
5. GNU ld、objcopy、strip 三种安装包变换后的程序均重新签名并真实运行，输出完全一致。

35 个最终保留 FAIL 的逐项证据见 `../ohos-failure-analysis.md`。

## 主机侧回传位置

```text
output/binutils-2.46.0/hdc-20260907/final39/
  binutils-hdc-final39-results.tar.gz
  binutils-hdc-final39-results.sha256
  final-build39/
  analysis/summary.json
  analysis/failures.json
  analysis/failure-classification.json
  analysis/failure-classification.md

output/binutils-2.46.0/hdc-20260907/runtime19/
output/binutils-2.46.0/hdc-20260907/runtime22/
output/binutils-2.46.0/hdc-20260907/runtime24/
output/binutils-2.46.0/hdc-20260907/runtime33/
output/binutils-2.46.0/hdc-20260907/runtime41/
```

`final20`、被归因门禁拒绝的 `final34` 和中断的 `final36` 均保留为历史证据，未覆盖。
