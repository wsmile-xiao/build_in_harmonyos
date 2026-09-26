# jellyfish 2.3.1 — OpenHarmony PC 适配笔记

## 一、上游识别

| 项 | 值 |
|---|---|
| 上游项目 | `gmarcais/Jellyfish` — DNA/RNA k-mer 计数工具（C++ / Autotools / libtool） |
| 版本 | 2.3.1（tag `v2.3.1`，2023-12-07 发布） |
| 官方源 | `https://github.com/gmarcais/Jellyfish/releases/download/v2.3.1/jellyfish-2.3.1.tar.gz` |
| sha256 | `ee032b57257948ca0f0610883099267572c91a635eecbd88ae5d8974c2430fcd`（1,151,250 字节） |
| 许可 | 双许可 BSD-3-Clause OR GPL-3.0（`LICENSE-BSD-3-Clause` / `LICENSE-GPL-3.0`） |
| 构建产物 | `bin/jellyfish`（CLI）+ `libjellyfish-2.0`（C++ 库）+ 头文件 + `jellyfish-2.0.pc` |

## 二、依赖分析（W0）

- **无强制第三方依赖**：configure.ac 仅可选探测 htslib（SAM/BAM/CRAM）与 SWIG 绑定（Python/Ruby/Perl）；未发现 zlib/libm 之外的链接需求。
- 本配方显式 `--disable-htslib`：保证构建可复现（避免构建机系统 htslib 意外命中），`tests/sam.sh` 按上游设计检查 `HAVE_HTSLIB` 后 `exit 77` 跳过。
- W0 检查：`conan download --only-recipe` 阶段无依赖需下载（dependencies: []）；制品仓中无 `jellyfish` 版本占用（`jellyfish/2.3.1` 首次适配）。

## 三、适配实现（6 个补丁，全部无平台宏）

1. `0001-config.guess.patch`：`uname -s = HarmonyOS` 未在 2018 版 config.guess 中，报 `cannot guess build type`。加 `HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl;`（E160），输出 `aarch64-unknown-linux-musl`。
2. `0002-configure.patch`：
   - config.status 用 `umask 077 && mktemp -d "./confXXXXXX"` 建临时目录；HMDFS 强制 setgid 与权限归一化后目录属主不可写，报 `config.status: ./confXXXXXX/subs1.awk: Permission denied`。去掉两处 `umask 077`（回退分支 `mkdir` 补 `2>/dev/null`）——E011/E114 标准解法。
   - 增加 `unix2dos` 功能探测：toybox 的 unix2dos 不支持测试脚本使用的 `-n <in> <out>` 语义，探测失败则置空 `UNIX2DOS`，上游测试中相应步骤自行跳过（`parallel_hashing.sh` 走 `cp` 回退分支）。
3. `0003-tests-bloom_counter.sh.patch` / `0004-tests-multi_file.sh.patch` / `0006-unit_tests-unit_tests.sh.patch`：命名管道（mkfifo）在 HarmonyOS 全局返回 EPERM（实测 `/dev/shm` 亦被拒，toybox 无 mkfifo 命令），因此对依赖 FIFO 的上游测试做**运行期能力探测**：
   - `bloom_counter.sh`：FIFO 可用时保持原样（generator 装载重复输入）；不可用时改用文件参数装载同一份重复输入（bc 内容一致，直方图 md5 不变）。
   - `multi_file.sh`：FIFO 不可用时跳过 generator 子测试并复用普通多文件直方图，仍保留"打不开文件必须失败"负例。
   - `unit_tests.sh`：FIFO 不可用时以 `--gtest_filter` 排除 `TmpPipes.*` 与 `GeneratorManager.OneLiners` 三个用例，其余 51310 个用例照常运行。
4. `0005-unit_tests-test_stream_iterator.cc.patch`：单元测试硬编码 `/tmp` 建临时目录；OHOS `/tmp` 只读（EROFS）。改为 `TMPDIR` → `/tmp` → `.` 依次尝试（E002 标准解法）。

## 四、上游测试账目（真实执行）

`conanfile.py build()` 内运行 `make check`（非 0 退出即构建失败），设备实测：

| 结果 | 数量 | 明细 |
|---|---|---|
| PASS | 10 | generate_sequence / parallel_hashing / merge / bloom_filter / subset_hashing / multi_file / bloom_counter / large_key / small_mers / unit_tests |
| SKIP | 5 | big（需 BIG=1，上游默认跳过）、sam（未启用 htslib，上游 exit 77）、swig_python/ruby/perl（未启用 SWIG 绑定，上游 exit 77） |
| FAIL | 0 | — |

单元测试内部：`[  PASSED  ] 51310 tests`，0 失败（FIFO 依赖 3 例按平台能力排除，日志有明确提示）。

## 五、鸿蒙特有测试（消费者视角）

`test_package/test.sh`：运行**已安装的** `jellyfish` CLI：
- 版本号精确匹配；`count -m 5 -C` 产出非空数据库；
- `histo` / `dump -c` 输出与黄金值逐行一致；
- `query`（显式 mer、反向互补归一化、从 FASTA 读取序列）结果精确匹配；
- `info` 读数据库头；
- 负例 2 条：缺失输入文件、缺失数据库必须被拒绝。
共 **11 条断言**（`MANIFEST.yml` assertion_count=11），0 失败。

## 六、平台限制（如实记录）

- **命名管道（mkfifo）不可用**：HarmonyOS 沙箱对 `mkfifo(2)` 返回 EPERM（实测 HMDFS/`/dev/shm` 均拒绝，且 toybox 未提供 mkfifo 命令）。因此 jellyfish 的 **generator 输入（`-g`/`-G`）在本平台不可用**；核心文件输入计数路径不受影响（已由上述测试覆盖）。该限制与用户/内核策略有关，本次以“运行期能力探测 + 跳过/回退”如实处理，未伪造任何测试通过状态。

## 七、知识沉淀

- 新平台模式草稿：`knowledge/drafts/DRAFT-7605-jellyfish-mkfifo-named-pipes-unavailable`（kv+md 成对；mkfifo EPERM → 运行期能力探测跳过/回退）。
- 已有条目复用：E160（config.guess HarmonyOS）、E011/E114（HMDFS umask）、E002（/tmp 只读）。

## 八、验证门禁（设备实测）

- `conan-verify`（G0–G4 + L2/L4/L5）：**全 PASS**（报告 `reports/conan-verify-report.md`，随 PR 提交）。
- `conan create` 干净构建：上游 `make check` **TOTAL=15 PASS=10 FAIL=0 SKIP=5**；消费者测试 **ASSERTIONS: 11, FAILURES: 0**（日志 `reports/conan-create.log`，本地证据不随 PR 提交）。
- 产物抽查：`bin/jellyfish`（arm64 ELF）`--version` → `jellyfish 2.3.1`。

**编译结束**: 2026-09-21
