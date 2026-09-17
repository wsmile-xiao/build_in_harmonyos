# DRAFT-lz4-1.10.0.3：lz4 1.10.0.x 配方 shared 构建目标缺失与 make SHELL 双环境自适应

> Contributor: gcw_6YxinkyD | Status: Draft | Updated: 2026-09-10
> Source: PR !9359 【知识库扩展】feat(lz4): 1.10.0.3 编译完成（真机 4 轮迭代）

## 背景

lz4 v1.10.0 为纯 Makefile 库（无 configure），仓库已有 1.10.0/1.9.4 配方且 CI
静态构建全绿。R37 升级版（首发 1.10.0.1，现按槽位顺延 1.10.0.3，同上游源码 + 适配修复后缀）在真机做
static + shared 双构建验证时，暴露两个**配方级**缺陷：一个只在 `shared=True`
时触发（CI 默认静态，从未执行到该分支），一个是环境路径硬编码。

## 坑 1：顶层 Makefile 无 `lib-shared` 目标（shared=True 必炸）

### 现象

```text
lz4/1.10.0: RUN: make lib-shared          # 1.10.0 配方 shared 分支
make: *** No rule to make target 'lib-shared'.  Stop.
```

### 根因（源码核实）

v1.10.0 顶层 `Makefile` 只有 `default: lib-release lz4-release`（liblz4.a + CLI），
**没有** `lib-shared` 目标；共享库目标在 `lib/Makefile`：

```make
.PHONY: lib
lib: liblz4.a liblz4        # 一次产出静态 + 带版本号共享库
```

1.10.0 配方因 CI 默认 `shared=False` 从未进入该分支，缺陷潜伏至真机
`-o shared=True` 验证才暴露。

### 修复

```python
if self.options.shared:
    self.run(make_cmd + " lib", cwd=self.source_folder + "/lib")
```

真机实证产物：`liblz4.so` / `liblz4.so.1` / `liblz4.so.1.10.0`。

## 坑 2：make 的 SHELL 硬编码 CI 路径，真机 Error 127

### 现象

```text
make: /data/service/hnp/bin/bash: No such file or directory
make: *** [Makefile:57: lib-release] Error 127
```

### 根因

- lz4 Makefile 的 recipe shell 需要 bash 级别特性，CI worker 的 /bin/sh 受限，
  1.9.4 配方引入 `SHELL=/data/service/hnp/bin/bash`（该路径仅 CI worker 存在）；
- **GNU make 4.4.1 忽略环境变量 SHELL**（POSIX 语义），profile [buildenv] 里
  的 SHELL 对 make 无效，必须在 make 命令行显式传递；
- 真机（frp 隧道设备）无该路径，但其默认 /bin/sh 可用（1.10.0 同源
  2026-08-31 全量测试 25 PASS 实证）。

### 修复（存在性自适应，双环境各有实证）

```python
make_vars = "POSIX_ENV=Yes CC=clang CXX=clang++ LN_SF=cp"
ci_bash = "/data/service/hnp/bin/bash"
if os.path.exists(ci_bash):
    make_vars += " SHELL=" + ci_bash
```

CI 命中 hnp bash（1.9.4 实证）；真机回退默认 /bin/sh（同源迭代真机
static + shared 双构建实证）。

## 附带：上游 tests/Makefile 用裸 cc

上游测试 Makefile 的编译命令未走 $(CC)，设备无 `cc` 别名时同样 Error 127；
执行上游测试须显式 `CC=clang`（配方内已传，直跑 tests 需自带）。

## 适用范围

- lz4 1.9.4 / 1.10.0.x 一切 shared 构建路径（`make -C lib lib` 范式）；
- 所有「顶层 Makefile 与子目录 Makefile 目标不对称」的库（shared 目标藏在
  lib/ 子 Makefile 的：xz 系、zstd 系同构）；
- 一切在 CI worker 与真机两种环境复用同一配方的 Makefile 库（SHELL/工具
  路径按存在性自适应，勿单环境硬编码）。

## 验证

真机隔离 CONAN_HOME：

```sh
conan create archives/l/lz4/1.10.0.3 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing            # static PASS
conan create archives/l/lz4/1.10.0.3 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 -o 'lz4/*:shared=True' --build=missing  # shared PASS
```

产物 liblz4.a 183KB / liblz4.so 三件套 / bin/lz4（--version 正常）；
test_package（含消费者用例）双轮 3/3 PASS。
