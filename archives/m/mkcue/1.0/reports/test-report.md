# mkcue 1.0 — 测试与验证报告

- 日期：2026-09-29
- 包引用：`mkcue/1.0@ohpcd/stable`（profile `ohos-aarch64`）
- 构建/测试命令（真实、逐条）见下方"命令与退出码"

## 一、上游测试（单独汇报）

| 指标 | 值 |
|------|-----|
| 上游自动化测试入口 | **不存在**（无 `tests/`、无 `check`/`test` 目标，见 `upstream-test-entry.md`） |
| 上游测试用例总数 | **0** |
| 通过 / 失败 / 跳过 | 0 / 0 / 0（无套件） |
| 上游样例（README 用法）用例总数 | **6** |
| 上游样例 通过 / 失败 / 跳过 | **6 / 0 / 0** |
| 不可测项 | 1（TOC happy path，需真实光驱；如实记录未伪装通过） |

上游样例逐项名称（全部实际执行，详见 `upstream-test-cases.md`）：

1. `upstream-default-device-open-error`
2. `upstream-explicit-device-open-error`
3. `upstream-trackcount-zero-rejected`
4. `upstream-trackcount-over-99-rejected`
5. `upstream-trackcount-one-accepted`
6. `upstream-unknown-option-usage`

## 二、test_package（消费者验证，不等于上游测试）

| 指标 | 值 |
|------|-----|
| 用例总数 | **9** |
| 通过 / 失败 / 跳过 | **9 / 0 / 0** |
| 其中鸿蒙平台特有 | **3**（≥1，满足要求） |

| # | 用例名称 | 类型 | 结果 |
|---|----------|------|------|
| 1 | `upstream-default-device-open-error` | 上游行为 | PASS |
| 2 | `upstream-explicit-device-open-error` | 上游行为 | PASS |
| 3 | `upstream-trackcount-zero-rejected` | 上游行为 | PASS |
| 4 | `upstream-trackcount-over-99-rejected` | 上游行为 | PASS |
| 5 | `upstream-trackcount-one-accepted` | 上游行为 | PASS |
| 6 | `upstream-unknown-option-usage` | 上游行为 | PASS |
| 7 | `ohos-elf-aarch64` | **鸿蒙平台** | PASS（`ELF Machine: AArch64`） |
| 8 | `ohos-elf-codesign-section` | **鸿蒙平台** | PASS（`.codesign` 段存在，E077） |
| 9 | `ohos-elf-musl-interpreter` | **鸿蒙平台** | PASS（`/lib/ld-musl-aarch64.so.1`） |

日志：`test_package/build-release/mkcue-cases.log`

## 三、安全与产物基线（L4/L5，手工复核）

`conan-verify` 的 L2/L4/L5 因缓存路径解析未命中而记为"跳过"，此处**手工补测**：

| 项 | 命令 | 结果 |
|----|------|------|
| 类型 / 架构 | `llvm-readelf -h bin/mkcue` | `Type: DYN (Shared object file)` / `Machine: AArch64`（PIE） |
| NX（不可执行栈） | `llvm-readelf -l` | `GNU_STACK … RW`（无 `E`）✅ |
| RELRO / BIND_NOW | `llvm-readelf -l` / `-d` | `GNU_RELRO` 段存在；`FLAGS: BIND_NOW`、`FLAGS_1: NOW PIE` ✅ |
| 解释器 | `llvm-readelf -l` | `/lib/ld-musl-aarch64.so.1`（OHOS musl） |
| OHOS 签名 | `llvm-readelf -S` | `.codesign` 段存在（E077）✅ |
| 产物基线 | `sha256sum bin/mkcue` | `31d3edb47aea682c6c0386828ec3f7117a1b0899ca3eeb47d35865efb796de1c` |

包内容：`bin/mkcue`（可执行，0o755）、`share/doc/mkcue/README`。

## 四、命令与退出码（真实记录）

| # | 命令 | 退出码 | 日志 |
|---|------|--------|------|
| 1 | `ohc-run.py init-build mkcue 1 --url=https://ftp.debian.org/debian/pool/main/m/mkcue/mkcue_1.orig.tar.gz` | 0 | `.task-logs/01-init-build.log` |
| 2 | `ohc-run.py lang-preflight mkcue 1 --src $BUILD_SRC_DIR` | 0（cpp 匹配） | `.task-logs/02-lang-preflight.log` |
| 3 | 上游测试入口核验（`find`/`grep`/`tar tzf`） | 0 | `.task-logs/03-upstream-test-entry.log` |
| 4 | `perl scripts/patch-autotools-ohos.pl build/config.guess build/config.sub` | 0（部分模式未命中，手工补齐） | `.task-logs/05-patch-autotools.log` |
| 5 | `./configure --prefix=… --host=aarch64-linux-ohos`（首次，未改 umask） | 0（但 `config.status` 报 Permission denied） | `.task-logs/07-configure.log` |
| 6 | `./configure --prefix=… --host=aarch64-linux-ohos`（umask 修复后） | 0 | `.task-logs/08-configure-rerun.log` |
| 7 | `make` | 0 | `.task-logs/09-make.log` |
| 8 | `make install DESTDIR=$TEST_PREFIX` | 0 | `.task-logs/10-install-and-smoke.log` |
| 9 | 原生冒烟（`mkcue -t 0` / 不存在设备 / 默认设备 / `-x`） | 2 / 2 / 2 / 2（符合设计） | `.task-logs/10b-smoke.log` |
| 10 | `python3 test_mkcue.py <bin> --log …` | 0（9/9） | `.task-logs/11-test-package-local.log` |
| 11 | `ohc-run.py conan-verify mkcue 1.0` | **0（G0–G4 PASS）** | `.task-logs/17-conan-verify.log`、`reports/conan-create.log` |
| 12 | `conan create … -pr:h=… -pr:b=… --build=missing --user=ohpcd --channel=stable`（内嵌于 11） | 0（含 test_package 9/9） | `reports/conan-create.log` |

## 五、未决/风险项

| 项 | 状态 |
|----|------|
| 上游版本字面为 `1`，Conan 版本正则要求 ≥2 字符 → 归一化为 `1.0` | 已处理（详见 `framework-findings.md`） |
| CI L0n 要求分支名精确等于 `mkcue-1.0`；本工作树分支已从 `feat/mkcue-1` 重命名为 `feat/mkcue-1.0` | 待确认 |
| 知识库 E490（autotools 脚本可执行位） | 配方已加防御性 `chmod 0o755`；本地未触发该故障 |
| TOC happy path | 无光驱，不可测（如实记录） |
