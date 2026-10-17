# 测试报告 — jellyfish 2.3.1 (OpenHarmony PC / OHOS aarch64)

> 目标平台：HarmonyOS PC（HongMeng Kernel 1.12.0，HAD-W32，aarch64）
> 工具链：OHOS SDK 26.0.0.18 原生 clang 15.0.4（libc++），Conan 2.29.1 (OHOS 适配版)
> 构建系统：Autotools（configure + make + libtool）
> 验证时间：2026-09-21

## 一、构建验证

| 步骤 | 命令 | 结果 |
|---|---|---|
| configure | `./configure --prefix=<prefix> --disable-htslib --disable-shared --enable-static` | 通过（补丁 0001/0002 生效） |
| 编译 | `make -j1` | 通过（仅有 1 条上游 `-Wunused-but-set-variable` 警告） |
| 上游测试 | `make check` | **PASS 10 / SKIP 5 / FAIL 0**（automake parallel-tests） |
| 单元测试 | `unit_tests/unit_tests.sh`（内置 gtest） | **51310/51310 通过**（3 个 mkfifo 用例按平台能力排除，日志声明） |
| 安装 | `make install` | bin/jellyfish、libjellyfish-2.0.a、include/jellyfish-2.3.1/、jellyfish-2.0.pc |
| 冒烟 | `jellyfish --version` | `jellyfish 2.3.1` |

### 上游测试明细（automake TESTS = 15）

```
PASS: tests/bloom_counter.sh
PASS: tests/bloom_filter.sh
PASS: tests/generate_sequence.sh
PASS: tests/large_key.sh
PASS: tests/merge.sh
PASS: tests/multi_file.sh
PASS: tests/parallel_hashing.sh
PASS: tests/small_mers.sh
PASS: tests/subset_hashing.sh
PASS: unit_tests/unit_tests.sh
SKIP: tests/big.sh            # 上游默认 skip（需 BIG=1）
SKIP: tests/sam.sh            # 未启用可选 htslib，上游 exit 77
SKIP: tests/swig_perl.sh      # 未启用 SWIG 绑定，上游 exit 77
SKIP: tests/swig_python.sh    # 未启用 SWIG 绑定，上游 exit 77
SKIP: tests/swig_ruby.sh      # 未启用 SWIG 绑定，上游 exit 77
# TOTAL: 15  PASS: 10  SKIP: 5  FAIL: 0  ERROR: 0
```

### 单元测试（gtest）摘要

```
[==========] 51310 tests from 52 test cases ran. (~100-190 s)
[  PASSED  ] 51310 tests.
PASS unit_tests/unit_tests.sh (exit status: 0)
```

排除的 3 个用例（平台能力，非缺陷）：`TmpPipes.CreateDestroy`、`TmpPipes.Discard`、
`GeneratorManager.OneLiners` —— HarmonyOS 全局拒绝 `mkfifo(2)`（EPERM），
测试脚本打印 `Named pipes (mkfifo) not available; excluding FIFO-based test cases`。

## 二、消费者测试（鸿蒙特有）

`test_package/test.sh`：对**已安装的** `jellyfish` CLI 执行 11 条断言（0 失败）：

| # | 断言 | 期望 |
|---|---|---|
| 1 | `--version` | `jellyfish 2.3.1` |
| 2 | `count -m 5 -s 100k -C` 产出非空数据库 | exit 0 且 out.jf 非空 |
| 3 | `histo` 精确输出 | `1 3;6 1;7 1;` |
| 4 | `dump -c` 精确输出（5 个 canonical 5-mer） | 排序后逐行一致 |
| 5 | `query ACGTA` | `ACGTA 7` |
| 6 | `query TACGT`（反向互补归一化） | `ACGTA 7` |
| 7 | `query -s t.fa` 行数 | 16 |
| 8 | `query -s t.fa` 中 `ACGTA 7` 命中数 | 7 |
| 9 | `info` 读数据库头 | exit 0 |
| 10 | 负例：输入文件缺失 | 非零退出 |
| 11 | 负例：数据库缺失 | 非零退出 |

## 三、适配补丁与根因

| 补丁 | 平台问题 | 处理 |
|---|---|---|
| 0001-config.guess | 2018 版 config.guess 不识别 `uname -s=HarmonyOS`，`cannot guess build type` | 加 `HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl`（E160） |
| 0002-configure | HMDFS 下 `umask 077 && mktemp -d ./confXXXXXX` 创建属主不可写目录（`config.status: subs1.awk: Permission denied`，E011/E114）；toybox unix2dos 不支持 `-n in out` | 去掉两处 `umask 077`；增加 unix2dos 功能探测 |
| 0003/0004/0006（测试） | `mkfifo(2)` 全局 EPERM（实测 `/dev/shm` 亦拒绝，toybox 无 mkfifo 命令） | 运行期能力探测：等价回退（bloom_counter）/ 跳过 generator 子测试（multi_file）/ gtest filter 排除 3 例（unit_tests），日志声明 |
| 0005（测试） | 单元测试硬编码 `/tmp`，OHOS `/tmp` 只读 EROFS（E002） | 改为 `TMPDIR` → `/tmp` → `.` 依次尝试 |

## 四、已知限制（如实披露）

1. **generator 输入不可用**：`jellyfish count -g/-G` 依赖命名管道，HarmonyOS 沙箱禁止 `mkfifo`；核心文件输入计数不受影响。若需该功能需重构 `generator_manager` 为匿名管道（`pipe()`/`socketpair()` + `dup2`）。
2. **htslib 未启用**：`--disable-htslib` 保证构建可复现；`tests/sam.sh` 按上游设计 exit 77。制品仓已有 `htslib/1.24-r0`，后续可加依赖启用。
3. **SWIG 绑定未启用**：上游默认不构建 Python/Ruby/Perl 绑定（需显式 `--enable-*`），3 个绑定测试按上游设计 skip。

## 五、Conan 配方验证（conan-verify，设备实测）

命令：`python3 scripts/ohc-run.py conan-verify jellyfish 2.3.1 --profile ohos-aarch64-device`
（内部执行 `conan create ... -pr:h=ohos-aarch64-device -pr:b=ohos-aarch64-device --user=ohpcd --channel=stable`，VPATH 构建）

| 门禁 | 结果 | 说明 |
|---|---|---|
| G0 预构建风险评估 | ✅ PASS | 知识图谱预查询（提示 E490 执行位风险，实际构建无此问题） |
| G1 配方完整性 | ✅ PASS | conanfile/conandata/test_package/MANIFEST 齐全，R26 静态链接配置存在 |
| G2 conan create（干净构建） | ✅ PASS | 完整 configure→make→`make check`→install→test_package；结果 `UPSTREAM 'make check' RESULTS: TOTAL=15 PASS=10 FAIL=0 SKIP=5 ERROR=0`；消费者测试 `ASSERTIONS: 11, FAILURES: 0` |
| G3 系统同名库隔离 | ✅ PASS | 无 `/lib`、`/lib64` 同名冲突 |
| G4 产物完整性 | ✅ PASS | bin/jellyfish + lib/libjellyfish-2.0.a + include + pkgconfig |
| L2 smoke test / L4 安全扫描 / L5 产物基线 | ✅ PASS | 见验证报告 |

报告：`reports/conan-verify-report.md`（随 PR 提交）；完整构建日志：`reports/conan-create.log`（本地证据，体积大不随 PR 提交）。

### 打包产物抽查

```
bin/jellyfish            ELF 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)
lib/libjellyfish-2.0.a   静态库
lib/pkgconfig/jellyfish-2.0.pc
include/jellyfish-2.3.1/jellyfish/*.hpp
$ bin/jellyfish --version  →  jellyfish 2.3.1
```
发布 tarball：`packaging/jellyfish-2.3.1-ohos-aarch64.tar.gz`（未入库，随 finish 生成）。

## 六、证据文件

| 文件 | 内容 |
|---|---|
| `reports/conan-create.log` | `conan create` 完整日志（含 `make check` 全量输出与测试计数；本地证据，不随 PR 提交） |
| `reports/conan-verify-report.md` | G0–G4 + L2/L4/L5 门禁报告（conan-verify） |
| `test_package/test.sh` | 消费者测试脚本（11 断言，含 2 负例） |
| `test_package/MANIFEST.yml` | 上游测试声明 + 断言数（11） |
| `notes.md` | 适配笔记与平台限制 |
