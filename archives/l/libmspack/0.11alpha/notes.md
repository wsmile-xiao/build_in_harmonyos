# libmspack 0.11alpha 编译笔记（HarmonyOS PC · Conan autotools）

## 定位与产物

- 上游官方发布 tarball（cabextract.org.uk），C 库，autotools 构建。
- 产物：`lib/libmspack.so.0.1.0`（+ `.so.0` / `.so` 软链）、`include/mspack.h`、
  `lib/pkgconfig/libmspack.pc`。无 `bin/` 可执行文件（examples/test 均为 noinst），
  故**不需要** commands.json（R38 仅命令行工具需要）。
- 参考实现：同软件 `archives/l/libmspack/1.11`（同一构建系统，配方骨架一致）。

## 与 1.11 的差异（0.11alpha 专有）

| 项 | 1.11 | 0.11alpha |
|----|------|-----------|
| 源码源 | GitHub tag 归档（`libmspack/` 子目录） | 官方发布 tarball（configure 在**顶层**） |
| configure 生成 | 归档无 configure，需 autoreconf | **自带 configure**（正常路径不 autoreconf） |
| 补丁 | 无 | 无（见下） |

- **删除历史遗留补丁**：2026-04-22 的 partial 尝试留下
  `patches/0001-config.guess.patch`、`patches/0002-config.sub.patch`。
  实测本 tarball 自带的 `config.sub`（文件内 timestamp `2022-01-03`）**已识别**
  `aarch64-unknown-linux-musl`（`./config.sub aarch64-unknown-linux-musl` → 原样回显，rc=0），
  且配方显式传 `--build/--host` 时 `config.guess` 根本不参与判定，
  故两个补丁均无必要，直接删除并在 `conandata.yml` 声明 `patches: {}`。

## 关键适配

- **三元组固定为 musl**：`generate()` 追加 `--build=aarch64-unknown-linux-musl`、
  `--host=aarch64-unknown-linux-musl`（与 1.11 同做法）。configure 实测：
  `checking build system type... aarch64-unknown-linux-musl`、
  `checking host system type... aarch64-unknown-linux-musl`、`checking whether we are cross compiling... no`。
- **make 单线程**：HMDFS 不支持 `mkfifo`，并行 make 会失败 → `autotools.make(args=["-j1"])`。
- **umask 修补位置**：对 `configure` 脚本本身把 `umask 077` 改成 `022`
  （否则 config.status 生成的文件在 HMDFS 下不可读）；若走 autoreconf 自举分支，
  该修补必须放在 autoreconf **之后**，否则会被重新生成的 configure 覆盖。
- **ELF 签名**：`package()` 里对 `lib/**/*.so*` 用
  `/data/service/hnp/bin/binary-sign-tool` 自签（XPM 要求，跳软链只签真实 ELF）。
- **测试接入构建**：`build()` 末尾执行 `make check`，使本地 W3 与 CI 的
  `conan create` 都覆盖上游测试（不是只在 PR 里贴一次结果）。

## R51 上游测试三步法

### 1) 清点（申报表）

| 项 | 内容 |
|----|------|
| 测试注册方式 | `Makefile.am`: `TESTS = $(check_PROGRAMS)` |
| 测试程序数 | 3（`test/cabd_test`、`test/chmd_test`、`test/kwajd_test`） |
| 夹具 | `test/test_files/{cabd,chmd,kwajd}`（EXTRA_DIST 随 tarball 发布，含真实 .cab/.chm/.kwj 与 CVE 回归样本） |
| 未注册的辅助程序 | `noinst_PROGRAMS`（examples/* 与 test/cabd_md5、chmd_find、chmd_md5、chmd_order、chminfo）——**上游未注册进 `make check`**，故不计入测试通过率 |

### 2) 实际运行（本机 W3 / conan create，构建期执行）

```
libmspack/0.11alpha@ohpcd/stable: RUN: make check -j1
  CCLD     test/cabd_test / test/chmd_test / test/kwajd_test
PASS: test/cabd_test
PASS: test/chmd_test
PASS: test/kwajd_test
Testsuite summary for libmspack 0.11alpha
# TOTAL: 3   # PASS: 3   # SKIP: 0   # XFAIL: 0
# FAIL:  0   # XPASS: 0  # ERROR: 0
```

日志：`reports/w3-local-ci.log` 的 `make check` 段（第 365-367 行三条 `PASS:`，
第 371-375 行 `# TOTAL: 3` / `# PASS: 3` / `# FAIL: 0`）。
注：`reports/conan-create.log` 是其后一次缓存命中的 test_package 复跑日志（仅 117 行），**不含** `make check` 输出。

### 3) 回填结果

| 指标 | 值 |
|------|----|
| 上游测试用例数 | 3 |
| 实测通过 | 3 |
| 失败 / 跳过 | 0 / 0 |
| 通过率 | 100% |
| 上游测试是否被修改 | 否（零改动，直接用上游注册的 3 个用例） |

补充：`test_package/test.c` 为**适配补全**的 API 断言（不属于上游用例，不参与上游通过率），
5 项断言全过：版本表差异化查询（LIBRARY=1 / MSCABD=2 / MSCABC=0）证明不是常量桩实现、
CAB 解压器真建真销毁、未知类型返回 -1（上游 `system.c` switch 落空分支）。

## 验证证据

- `conan-verify` 门禁：**Verdict PASS**（G0/G1/G2/G3/G4 通过；其中 G4 附
  “无法找到程序包 ID” 告警；L2/L4/L5 该次因无 cache 路径被**跳过**，并非实质通过），
  报告见 `reports/conan-verify-report.md`。
- `conan create`（profile `ci/conan/profiles/ohos-aarch64`，`--build=missing --user=ohpcd --channel=stable`）：
  包 id `01d92cf349a0dd98ff915f4bd99a04430171517f`（armv8 / OHOS / clang 15 / Release / shared=True），
  完整构建 + `make check` 日志 `reports/w3-local-ci.log`（W3 本地 CI 模拟）；
  `reports/conan-create.log` 为随后缓存命中的 test_package 复跑日志。
- `test_package`：`RUN: /data/service/hnp/bin/bash -c './test_probe'` → `libmspack 0.11alpha: 全部断言通过`。

## 状态

built（G0-G4 通过，可发布；待 CI conan create + L4/L5 复核）
---

**编译结束**: 2026-09-25 11:15
**最终状态**: built
