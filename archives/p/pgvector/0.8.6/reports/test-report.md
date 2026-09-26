# pgvector 0.8.6 验证报告（OHOS PC aarch64）

## 1. 环境

| 项 | 值 |
|----|----|
| 平台 | OpenHarmony / HarmonyOS PC，aarch64（本机原生构建，非交叉） |
| 编译器 | clang 15.0.4（`/data/service/hnp/bin/clang`，经 `pg_config --cc` 由 PGXS 取用） |
| 构建依赖 | `postgresql/18.3`（ohpcd 制品仓，tool_requires） |
| profile | `ci/conan/profiles/ohos-aarch64`（host = build） |

## 2. 编译验证

```
conan create archives/p/pgvector/0.8.6 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
→ exit code 0
```

- 编译告警：0（19 个翻译单元，`-Wall -Werror=vla ...` 全清）
- 产物：`lib/vector.so` 203200 B、`extension/{vector.control, vector--*.sql}`（41 个 SQL，含 40 个升级脚本）、
  `upstream/test/{sql,expected}`（上游回归资产）
- ELF 事实：`NEEDED libc.so`（musl）唯一；无 SONAME；无 RPATH/RUNPATH；含 `.codesign` 段

## 3. 上游测试（实测执行）

驱动：`test_package/pgvector_test.py`（由 `conan create` 的 test 阶段实跑）

```
HMBS_UPSTREAM_TEST_RESULT={"status": "passed",
  "discovered": 14, "executed": 14, "passed": 14, "failed": 0,
  "command": "initdb -> pg_ctl start -> CREATE EXTENSION vector -> psql -X -a -q per group"}
```

| 用例组 | 结果 |
|--------|------|
| vector_type | ok |
| bit | ok |
| cast | ok |
| copy | ok |
| halfvec | ok |
| sparsevec | ok |
| btree | ok |
| hnsw_vector / hnsw_halfvec / hnsw_bit / hnsw_sparsevec | ok |
| ivfflat_vector / ivfflat_halfvec / ivfflat_bit | ok |
| **合计** | **14/14（100%）** |

比对口径：每组 `psql -X -a -q -d regression`（脚本经 stdin）合并 stdout+stderr 后与
`test/expected/<name>.out` 逐字节相等。

未执行：`test/t/*.pl` 48 个 Perl TAP 脚本 —— 依赖 Perl 模块 `IPC::Run`，OHOS perl 5.42 不存在该模块
（`perl -MIPC::Run -e1` → `Can't locate IPC/Run.pm`），无可用 conan 依赖可补，CI 环境同样不具备。

## 4. 新增/消费者测试（实测执行）

```
HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": true,
  "discovered": 13, "passedCount": 13,
  "breakdown": {"consumer": 9, "ohos": 2, "pc": 2}}
```

| 组 | 用例 | 实测值 |
|----|------|--------|
| 消费者 | C1 `CREATE EXTENSION vector` 生效 | extversion `0.8.6` |
| 消费者 | C2 vector 文本往返 | `[1.5,-2,3.25]` |
| 消费者 | C3 halfvec/sparsevec/bit 三类型可用 | `{1:1,3:2}/3\|[1,2]\|101` |
| 消费者 | C4 `<->` / `<#>` / `<=>` 距离算子 | `5.196152422707` / `-32.000000000000` / `0.025368153803`（与 Python 参考值差 < 1e-9） |
| 消费者 | C5 ivfflat 索引构建 + 精确近邻 | nearest id=69（probes=lists，精确） |
| 消费者 | C6 hnsw 索引构建 + 精确近邻 | nearest id=69（ef_search=100，精确） |
| 消费者 | C7 ivfflat/hnsw 访问方法注册到 `pg_am` | `hnsw,ivfflat` |
| 鸿蒙特有 | H1 动态依赖仅 musl `libc.so`（无 glibc `libc.so.6`） | `DT_NEEDED=['libc.so']` |
| 鸿蒙特有 | H2 目标数据模型 ELF64 / 小端 / AArch64(LP64) | `e_machine=183` |
| PC 特有 | P1 含鸿蒙 PC ELF 加载签名段 | `.codesign` present |
| PC 特有 | P2 无 RPATH/RUNPATH、无构建机绝对路径 | 可重定位 |
| **合计** | | **13/13（100%）** |

消费者测试驱动入口：`test_package/conanfile.py` 的 `test()` 在 `conanbuild` 环境下执行上述 13 项断言
（同一批断言，不重复计入合计）。

## 5. 复现命令

```bash
export OHC_PROJECT_DIR=$PWD
conan create archives/p/pgvector/0.8.6 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```
