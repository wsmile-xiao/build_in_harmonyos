# pgtap 1.3.4 验证报告（OHOS PC aarch64）

## 1. 环境

| 项 | 值 |
|----|----|
| 平台 | OpenHarmony / HarmonyOS PC，aarch64（设备原生构建，`uname`：HongMeng Kernel 1.12.0 aarch64） |
| 编译器 | clang 15.0.4（`~/.harmonybrew/opt/ohos-sdk@26.0.0.18/native/llvm/bin/clang`） |
| 构建依赖 | `postgresql/18.3`、`perl/5.42.2.3`（ohpcd 制品仓，均为 `tool_requires`） |
| profile | `ohos-aarch64-device`（device 版，host = build） |
| 构建系统 | 上游 PGXS（`make all`，无 configure） |

## 2. 编译验证

```
conan create archives/p/pgtap/1.3.4 -pr:b=ohos-aarch64-device -pr:h=ohos-aarch64-device
→ exit code 0
```

- 产物（包内）：`extension/` 26 个文件（`pgtap.control` + 25 个 SQL：安装脚本 370926 B /
  1085 个 `CREATE OR REPLACE FUNCTION`、17 个历史升级脚本 + unpackaged、pgtap-core /
  pgtap-schema 的版本化与 unversioned 件、uninstall_pgtap.sql）、
  `upstream/test/{sql,expected}`（37 sql / 54 expected）、`doc/pgtap.mmd`
  （上游发布 tarball 不含 LICENSE 文件，故无 licenses/ 目录）
- 无编译产物（纯 SQL 扩展）；无构建机路径泄漏（扫描 26 个文件通过）

```
python3 scripts/ohc-run.py conan-verify pgtap 1.3.4 --profile ohos-aarch64-device
→ G0 PASS / G1 PASS / G2 PASS / G3 PASS / G4 PASS / L2 PASS / L4 PASS / L5 PASS
```

## 3. 上游测试（实测执行，R51）

驱动：`test_package/pgtap_test.py`（由 `conan create` 的 test 阶段实跑）；PG 18.3 临时实例，
TCP loopback（`unix_socket_directories=''`），`extension_control_path=<包目录>:$system` 免拷贝加载。

```
HMBS_UPSTREAM_TEST_RESULT={"status": "passed",
  "discovered": 37, "executed": 38, "passed": 38, "failed": 0, "skipped": 1,
  "command": "make installcheck equivalent: initdb -> pg_ctl start -> psql -X -a -q per group -> byte-exact diff against test/expected"}
```

| 用例组 | 结果 |
|--------|------|
| build / create（schedule 生成 setup 组） | ok / ok |
| aretap, check, cmpok, coltap, do_tap, enumtap | ok ×6 |
| fktap, functap, hastap, index, inheritance, istap | ok ×6 |
| matching, moretap, ownership, partitions | ok ×4 |
| performs_ok, performs_within, pg73, pktap, policy, privs | ok ×6 |
| proctap, resultset, roletap, ruletap | ok ×4 |
| runjusttests, runnotests, runtests | ok ×3 |
| throwtap, todotap, trigger, unique, usergroup, util, valueset | ok ×7 |
| **合计** | **38/38（100%）** |

比对口径：每组 `psql -X -a -q -d contrib_regression`（脚本经 stdin）合并 stdout+stderr 后与
`test/expected/<name>.out` 逐字节相等（支持 `_N.out` 备用输出），等价复刻 `make installcheck`
（`postgresql/18.3` 包未随附 `pg_regress` 二进制）。

跳过：`extension.sql` —— 依赖 `citext`/`isn`/`ltree`，`postgresql/18.3` 不含 contrib；
与上游 Makefile 在 `MISSING_EXTENSIONS` 下的排除逻辑一致。
不可执行：`update.sql` 属 `make updatecheck`（需联网从 PGXN 安装 pgtap 0.95.0 后
`ALTER EXTENSION UPDATE`），不在 `make installcheck` 用例集中。

## 4. 本地断言（消费者 + 制品 + 鸿蒙特有，实测执行）

```
HMBS_TEST_PACKAGE_RESULT={"executed": true, "passed": true,
  "discovered": 17, "passedCount": 17, "failedCount": 0,
  "breakdown": {"artifact": 8, "consumer": 9}}
```

| 组 | 用例 | 实测值 |
|----|------|--------|
| 制品 A1 | `pgtap.control` 字段完整（1.3.4 / plpgsql / relocatable） | 3 项字段存在 |
| 制品 A2 | 安装脚本完整 | 1085 个函数, 370926 bytes |
| 制品 A3 | TAP API 入口齐备（plan/ok/is/has_table/col_not_null/finish） | 6/6 存在 |
| 制品 A4 | `os_name()` 钉为 harmonyos（OSNAME 注入生效） | `harmonyos` |
| 制品 A5 | 历史升级脚本链完整 | 18 个 `--*--*.sql` |
| 制品 A6 | 基础/版本化 bundle 齐备（pgtap/core/schema 版本化 + unversioned + uninstall） | 7/7 |
| 制品 A7 | 无构建机绝对路径泄漏 | 扫描 26 个文件 |
| 制品 A8 | 上游回归资产随包 | 37 sql / 54 expected |
| 消费者 C1 | `CREATE EXTENSION pgtap` 生效（control+SQL 从包目录解析） | rc=0 |
| 消费者 C2 | `extversion` | `1.3.4` |
| 消费者 C3 | `pgtap_version()` | `1.3` |
| 消费者 C4 | `os_name()` 平台标识 | `harmonyos` |
| 消费者 C5 | `pg_version_num()` 匹配 PG 18 | `t` |
| 消费者 C6 | TAP mini-suite（plan/ok/is/isnt/finish） | 3 行 ok, 0 失败 |
| 消费者 C7 | **负向对照**：故意失败断言必须报 `not ok` | `not ok 1 - deliberately wrong` |
| 消费者 C8 | schema 断言（has_table/has_column/col_not_null/col_is_pk） | 4 行 ok, 0 失败 |
| 消费者 C9 | lives_ok / throws_ok 行为正确 | 2 行 ok, 0 失败 |
| **合计** | | **17/17（100%）** |

说明：本包为纯数据扩展，无 bin/lib/include，CI L1e 破坏性反向验证会因无标准产物目录而跳过；
C7 负向对照（故意失败断言必须被报为 `not ok`）从行为层证明测试非空壳、断言真实生效。

## 5. 关键问题分析

### 问题 1: conan perl 核心模块不可见

**现象**：`compat/gencore` 报 `Can't locate strict.pm in @INC (//lib/perl5/...)`。

**根因**：conan perl 包按空前缀安装，内建 @INC 指向 `//lib/perl5/...`。

**解决方案**：构建命令前置 `PERL5LIB=<perl包>/lib/perl5`。

### 问题 2: `os_name()` 生成空串

**现象**：设备 shell 下 `tools/getos.sh` 报 `alias: -e: invalid alias name` 并输出空串，
生成的 `os_name()` 返回 `''`，会破坏上游 `util.sql` 的
`matches(os_name(), '^[[:alnum:]]+$')`。

**根因**：getos.sh（Perl Configure 的 uname 解析器）内部 `command -v sed` 在设备 shell
取到的是别名定义，后续 `$sed -e ...` 被当作 `alias` 命令执行而失败。

**解决方案**：make 命令行显式 `OSNAME=harmonyos`（上游文档化变量），设备与 CI 产物一致。

## 6. 复现命令

```bash
# 在 pgtap 任务工作树根目录执行（profile 为设备适配版 ohos-aarch64-device）
conan create archives/p/pgtap/1.3.4 \
  -pr:b=ohos-aarch64-device -pr:h=ohos-aarch64-device
```

---

*报告生成时间: 2026-10-01*
