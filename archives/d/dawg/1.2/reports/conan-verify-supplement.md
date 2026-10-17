# dawg 1.2 — conan-verify 跳过项人工补测报告

`conan-verify` 的 `reports/conan-verify-report.md` 中 G4 报 `⚠️ 无法找到程序包 ID`，
L2/L4/L5 均打印 `✅ PASS` **同时**标注 `⏭️ 跳过（无 cache 路径）`。按 workflow 第 7.2 节
口径，`✅ PASS` 与 `⏭️ 跳过` 并存时以**跳过**为准。本包是 `package_type = "application"`
的纯可执行包（包内无 `lib/`、无 `include/`，G3 自己就打印 `ℹ️ 无 lib/ 目录（纯可执行包）`），
整组命中该已知缺陷，因此按第 7.2 节「application 包同样必须人工补测」逐项补测如下。

- 被测包引用：`dawg/1.2@ohpcd/stable`
- 包目录（glob 定位）：`${CONAN_HOME}/p/*/dawg*/p`
- 补测依据的构建轮：本文记录的全部产物哈希与行为断言**只依赖包内容**，已在同一提交上
  做两轮清缓存构建验证逐字节可复现（见 L5），两轮的缓存分片目录名必然不同
  （每轮重建）但 16 个内容产物逐字节一致。

---

## G4 — 声明产物真实存在（补测）

判据：`find <包目录> -type f` 的清单与 `package_info()` 声明的 `bindirs` 互相印证
（本包 `bindirs = ["bin"]`，`libdirs = []`，`includedirs = []`）。

```
$ find <包目录> -type f | sed 's|<包目录>/||' | sort
bin/dawg
conaninfo.txt
conanmanifest.txt
doc/dawg-1.2-release/changelog.txt
doc/dawg-1.2-release/copying.txt
doc/dawg-1.2-release/readme.txt
licenses/copying.txt
share/applications/dawg.desktop
share/dawg-1.2-release/examples/example0.dawg
share/dawg-1.2-release/examples/example1.dawg
share/dawg-1.2-release/examples/example2.dawg
share/dawg-1.2-release/examples/example3.dawg
share/dawg-1.2-release/examples/example4.dawg
share/dawg-1.2-release/lambda.pl
share/dawg-1.2-release/nexus2fasta.pl
share/dawg-1.2-release/outsplit.pl
share/dawg-1.2-release/varrep.pl
share/pixmaps/dawg.png
```

- 文件总数 18（其中 `conaninfo.txt`/`conanmanifest.txt` 为 Conan 元数据）。
- 可执行产物 `bin/dawg`（195072 字节）存在，与 `package_info()` 的 `bindirs = ["bin"]` 一致。
- `lib/` 目录不存在 → 与 `libdirs = []` 一致；`.so`/`.a` 一个都没有（R26 静态/无库交付）。
- 上游 `cmake --install` 的 `RUNTIME DESTINATION bin` 规则把唯一可执行文件落进 `bin/`，
  与 `commands.json` 的 `type: "tool"` 声明一致。

---

## L2 — 消费者实际行为（补测）

判据：按可执行包口径用**包内制品**跑真实命令，断言业务输出而非仅退出码。

```
$ PATH="<包目录>/bin:$PATH" command -v dawg
<包目录>/bin/dawg                     # 确认取到的是包内制品，不是构建树或系统副本
$ PATH="<包目录>/bin:$PATH" dawg --version | head -1
dawg 1.2-release                      # 程序自报身份
```

在只设 `PATH`（**不设** `LD_LIBRARY_PATH`）的条件下运行完整消费者测试
`test_package/test.sh`（该脚本由 `test_package/conanfile.py` 在 conanrun 环境调用，
此处复用于包内制品）：

```
TEST_PACKAGE_RESULT: PASS 16/16 assertions
```

16 项断言的完整 PASS 行已随本 PR 入库：`reports/l2-supplement.log`（可直接 `tail` 复核）。
逐项清单：

| # | 断言 |
|---|------|
| 1 | `--version` 自报 `dawg 1.2-release` |
| 2 | `--help` 打印程序描述与变量表 |
| 3 | test0 配置输出与 golden **逐字节一致**（555 字节） |
| 4 | 输出 5 条带标签序列 |
| 5 | 节点标签 A/B/C/D/R 齐全（树 `((A,B)D,C)R` 全部节点落盘） |
| 6 | 比对字母表仅 ACGT 与 gap 字符 |
| 7 | 比对矩形：5 条序列等长，长度 105 |
| 8 | 同一 seed 两次运行逐字节一致（确定性） |
| 9 | `Seed` 变化改变输出（RNG 真的接线） |
| 10 | Nexus 格式：有 `#NEXUS` 头且 `DIMENSIONS NTAX=5` |
| 11 | Phylip 格式：首行为 `5 105` |
| 12 | Clustal 格式：含 `CLUSTAL` 头 |
| 13 | `GapModel` NB/PL/US 三种模型均产出 5 条序列的比对 |
| 14 | PL 非法参数被拒绝并给出上游诊断（参数校验真实生效） |
| 15 | CLI `-o` 选项写出与 golden 一致的比对文件 |
| 16 | 运行未改写输入夹具 |

补充：`dawg --version` / `dawg --help` 退出码均为 0（该程序把 usage 打到 stdout，
未识别的长选项告警打到 stderr），不属第 17 节 W3 L2 只试 GNU 长选项导致的 skip 场景。

---

## L4 — 安全属性（补测）

判据：对 `bin/` 下可执行文件逐个取 `readelf -h/-lW/-dW`，核对
`DYN` + `GNU_STACK RW` + `GNU_RELRO` + `FLAGS BIND_NOW` + `FLAGS_1 PIE`。

```
$ readelf -h <包>/bin/dawg | grep -E "Type:|Machine:"
  Type:    DYN (Position-Independent Executable file)
  Machine: AArch64

$ readelf -lW <包>/bin/dawg | grep -E "GNU_STACK|GNU_RELRO"
  GNU_RELRO  0x01e0b0 0x00000000000200b0 0x00000000000200b0 0x0009b0 0x000f50 R   0x1
  GNU_STACK  0x000000 0x0000000000000000 0x0000000000000000 0x000000 0x000000 RW  0

$ readelf -dW <包>/bin/dawg | grep -E "FLAGS|BIND_NOW|NEEDED"
  (NEEDED)   Shared library: [libc++_shared.so]
  (NEEDED)   Shared library: [libc.so]
  (FLAGS)    BIND_NOW
  (FLAGS_1)  Flags: NOW PIE
```

| 检查项 | 结果 |
|--------|------|
| 位置无关可执行（PIE） | ✅ `Type: DYN` + `FLAGS_1: PIE` |
| 栈不可执行（NX） | ✅ `GNU_STACK ... RW`（无 E） |
| RELRO | ✅ `GNU_RELRO` 段存在 |
| 立即绑定 | ✅ `FLAGS: BIND_NOW`（+ `FLAGS_1: NOW`） |
| 动态依赖最小化 | ✅ 仅 `libc++_shared.so` 与 `libc.so` |

可执行性判据按第 7.2 节取「退出码 ≠ 126」（内核拒绝 exec）：`dawg --version` rc=0，
且上述 16 项业务断言全部真实执行通过，不存在 `Operation not permitted` 类拒绝。

---

## L5 — 产物基线与可复现性（补测）

按第 7.2 节「先做可复现性判别再给基线」执行：同一提交、**两轮清缓存**构建
（每轮前执行 `conan remove` 限 ref/裸 ref + 删分片目录 + `cache.sqlite3` 两表回查为空），
逐产物比对 sha256。

```
$ cd archives/d/dawg/1.2/reports
$ diff <(grep -v -e conaninfo.txt -e conanmanifest.txt l5-roundA.sha256 | sort -k2) \
       <(grep -v -e conaninfo.txt -e conanmanifest.txt l5-roundB.sha256 | sort -k2)
（无输出）→ 16 个内容产物逐字节一致（构建可复现）
```

（不要对两张表直接 `diff`：`conanmanifest.txt` 含打包时间戳，必然出现一行差异，原因见下节。）

两轮的缓存分片目录名必然不同（每轮重建，含 `dawg` 前 5 字符 + 哈希）属预期，
故聚合命令一律在包目录内用**相对路径**（见第 7.2 节口径）；本报告不引用具体目录名，
以免下一轮重建后不可复核。

**稳定基线（两条聚合均排除 `conaninfo.txt`/`conanmanifest.txt`，因其首行是打包时间戳）**

| 基线 | 值 |
|------|-----|
| 包内容聚合（相对路径，排除元数据） | `cfa821d87f56fbe1f78d3a323ba3f2997f414de91f8236a000b13502fdfe877a` |
| 唯一可执行产物 `bin/dawg` | `b21fcfd50760e1efdc9e3acbc34a955874aba2f0bbd63907e7e7017ae8c32b20` |

复算命令：

```sh
PKG=$(ls -d "${CONAN_HOME:-$HOME/.conan2}"/p/*/dawg*/p | head -1)
cd "$PKG" && find . -type f ! -name conaninfo.txt ! -name conanmanifest.txt \
  | sed 's|^\./||' | sort | xargs sha256sum | sha256sum
sha256sum "$PKG/bin/dawg"
```

逐产物 sha256 全表已随本 PR 入库：`reports/l5-roundA.sha256` 与 `reports/l5-roundB.sha256`
（各 18 行 = 16 个内容产物 + `conaninfo.txt` + `conanmanifest.txt`）。
注意两张表**直接 `diff` 并非无输出**：`conanmanifest.txt` 的首行是打包时间戳（实测为 epoch 整数），
其哈希在两轮间必然不同（属预期）；`conaninfo.txt` 实测两轮哈希**相同**
（`0b387f2422bd81d5…`，其首行是 `[settings]` 而非时间戳），把它一并排除只是让口径更保守。
**排除这两份元数据后的 16 个内容产物两轮 diff 无输出**，这正是上一节聚合基线的口径。复算：

```sh
cd archives/d/dawg/1.2/reports
diff <(grep -v -e conaninfo.txt -e conanmanifest.txt l5-roundA.sha256 | sort -k2) \
     <(grep -v -e conaninfo.txt -e conanmanifest.txt l5-roundB.sha256 | sort -k2)   # 无输出
```

含 `doc/`、`share/` 等安装文件在内的全部内容产物在两轮间逐字节一致，未出现 `__DATE__`/`__TIME__`
或调试目录名导致的漂移（本包 `Release` 构建；上游仅在运行期 `rand_seed()` 取 `time(NULL)`，
不影响制品字节）。

---

## 结论

| 门禁 | 工具报告 | 人工补测结论 |
|------|---------|-------------|
| G4 | ✅ PASS（但 `⚠️ 无法找到程序包 ID`） | ✅ 18 个产物与 `bindirs=["bin"]`/`libdirs=[]` 互证 |
| L2 | ✅ PASS + ⏭️ 跳过 | ✅ 包内制品 16/16 断言真实通过 |
| L4 | ✅ PASS + ⏭️ 跳过 | ✅ PIE + NX + RELRO + BIND_NOW，依赖最小化 |
| L5 | ✅ PASS + ⏭️ 跳过 | ✅ 两轮清缓存构建逐字节可复现，已给稳定基线 |

上游测试侧的真实计数（采信轮 `reports/conan-create.log`）：
`UPSTREAM RUN: test0.dawg records=5 alignment_length=105 raw_bytes=555`、
`UPSTREAM TEST: tests/test0.sh PASS 1/1`，即 TOTAL=1 / PASS=1 / FAIL=0 / SKIP=0 / NOT_RUN=0。
