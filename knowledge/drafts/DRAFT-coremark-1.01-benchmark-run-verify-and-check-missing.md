# coremark 1.01：EEMBC 基准程序适配要点（run 自校验验证 + make check 发行物缺失判定）

- **草稿 ID**: `DRAFT-coremark-1.01-benchmark-run-verify-and-check-missing`
- **来源**: `coremark/1.01` HarmonyOS PC 适配实战（pc7-8，第一轮）
- **分类**: `benchmark / raw-makefile / ohos / conan / testing`
- **状态**: `VERIFIED DRAFT`，路径 B 难度候选，待知识库审核
- **Issue/PR**: 本轮按任务要求不记录

## 适用场景

coremark 1.01（EEMBC CoreMark 基准）是纯 Makefile 构建的自校验基准程序（无
configure、无 tests/ 目录、无 ctest/GTest 注册）。在 HarmonyOS PC（AArch64、
musl）上适配时，遇到三类平台无关陷阱，适合以下组合场景：

- 目标是 EEMBC 系基准/自校验型 Makefile 程序（coremark、coremark-pro 及同类）；
- 需要以 `run` 目标（VALIDATION_RUN/PERFORMANCE_RUN/PROFILE_RUN）作为权威验证入口；
- 官方 GitHub tag 不含发行包专有文件（coremark.md5），`make check` 必然失败。

## 问题与错误签名

### 1. PORT_DIR 缺失

```text
Makefile:45: *** PLEASE define PORT_DIR! (e.g. make PORT_DIR=simple).  Stop.
```

coremark Makefile 在未定义 PORT_DIR 时依赖 `uname` 自动判定（Linux 64 位 →
linux64），显式指定才可靠、可复现。

### 2. `make check` 失败（发行包专有文件缺失）

```text
$ make PORT_DIR=linux64 check
md5sum -c coremark.md5
md5sum: coremark.md5: No such file or directory
make: *** [Makefile:136: check] Error 1
```

官方 GitHub tag v1.01 源码树**不含** `coremark.md5`——该文件仅存在于 EEMBC
完整发行包，`check` 目标专为其设计。**属上游分发行为，不是当前库适配缺陷**，
不得把该失败写成当前库质量结论，也不得伪造该文件。

### 3. 验证运行时长窗口

```text
ERROR! Must execute for at least 10 secs for a valid result!
```

验证运行迭代数不足时 coremark 拒绝给出有效结果（Errors detected）。需要
`-DITERATIONS` 显式设定或让迭代数足够；用固定种子 + 足够迭代时输出
`Correct operation validated`。

## 修复方案

### 配方层（conanfile.py）

```python
# R33: get compiler from Conan conf, never from bare shell env vars
compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
cc = compilers.get("c", "clang") if compilers else "clang"
# coremark: plain Makefile, no configure. linux64 port layer, iterations fixed.
self.run(
    f"make PORT_DIR=linux64 CC={cc} EXE='' XCFLAGS='-DITERATIONS=1000' -j1",
    cwd=self.source_folder,
)
```

- `PORT_DIR=linux64`：显式指定移植层，避免 uname 判定漂移；
- `EXE=''`：去掉 linux64 移植层默认的 `.exe` 后缀，产物名为 `coremark`；
- `XCFLAGS='-DITERATIONS=1000'`：固定迭代次数，控制运行窗口；
- `cwd=self.source_folder` + conf 取编译器：raw makefile 配方三要素（E392）。

### conandata.yml

codeload URL 末段无扩展名，必须显式声明 `filename`（否则 BadZipFile，E276/E392/E483）：

```yaml
sources:
  url: "https://codeload.github.com/eembc/coremark/tar.gz/refs/tags/v1.01"
  filename: "coremark-1.01.tar.gz"
  sha256: "99c5a6d63af85a281b4e4d6ccb522c446653c435dfec9455ad73ef9e71f28bde"
```

### 验证层（权威入口 = run 目标自校验）

```bash
make PORT_DIR=linux64 CC=clang XCFLAGS="-DITERATIONS=1000 -DPERFORMANCE_RUN=1" load run1.log
make PORT_DIR=linux64 CC=clang XCFLAGS="-DITERATIONS=1000 -DVALIDATION_RUN=1" load run2.log
make PORT_DIR=linux64 CC=clang XCFLAGS="-DITERATIONS=1000 -DPROFILE_RUN=1" load run3.log
```

断言 `Correct operation validated` 与固定种子参考值 **seedcrc=0x18f2**
（由固定种子 0x3415 0x3415 0x66 决定，与迭代次数无关，上游 run2.log 同值）。

鸿蒙专项测试（`test_ohos/run_ohos_test.sh`）逐项验证：aarch64 ELF / OHOS musl
动态链接器 / 无宿主路径泄漏 / 验证运行（Correct operation validated +
seedcrc=0x18f2 + 无 Errors detected）。

## 验证

- run1.log：15551.29 it/s，`Correct operation validated`（PASS）
- run2.log：15344.48 it/s，seedcrc=0x18f2，`Correct operation validated`（PASS）
- run3.log：65915.63 it/s，`Correct operation validated`（PASS）
- 鸿蒙专项 T1-T4：ALL PASS
- W3 本地 CI（build_and_test.sh）：L0-L5 全 pass，`.ci-result.json` exit_code=0
- conan-verify G1-G4：PASS

## 适用范围

- EEMBC 系基准/自校验型 Makefile 程序（coremark、coremark-pro 及同类）；
- "官方 tag 不含发行包专有 check 文件"（md5/签名/校验文件仅随完整发行包分发）
  的通用判定：记录为上游分发缺失，计入台账但不计入测试分母；
- 同型：任何 `make check` 依赖发行包专有文件的上游。

## 反例/边界

- 带真实测试框架（ctest/pytest）的库**不适用**"run 即验证"语义；
- `make check` 在从 EEMBC 完整发行包获取 coremark.md5 后可用，但配方不得伪造该文件；
- crcfinal 随迭代次数变化，**不能**作为固定参考断言；seedcrc 由固定种子决定，可作参考。

## 查重

四范围（index.tsv / doc / graph/*.kv / drafts）零命中；与 E392（raw makefile
配方三要素）、E276/E483（BadZipFile）为 similar_to 关系，触发器不同、新增
"基准 run 自校验验证 + check 发行物缺失判定"组合。七轴详见
`archives/c/coremark/1.01/reports/knowledge-candidate-ledger.md`。

*生成时间：2026-09-20；执行端 pc7-8；task_id: coremark-1.01-r01-pc7-8-20260920T150648Z*
