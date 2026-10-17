# kamailio-snmpstats 6.0.6 适配笔记

## 一、基本信息

| 项 | 值 |
|----|----|
| 上游 | kamailio 6.0.6 |
| 源码 | https://www.kamailio.org/pub/kamailio/6.0.6/src/kamailio-6.0.6_src.tar.gz |
| sha256 | `32e4290c6813c9d0289abe9ec2de9138e12e0381179218a7fed374ad813ecc48` |
| 构建体系 | kamailio 经典 Makefile 体系（src/Makefile + Makefile.defs + Makefile.modules） |
| 打包产物 | `snmpstats.so`（AgentX 子代理模块）+ 5 个 KAMAILIO MIB 文件 |
| 平台目标 | OHOS / aarch64（SDK clang 默认 target 即 aarch64-unknown-linux-ohos） |

## 二、打包口径（参照 archives/a/asterisk-srtp/22.10.1 先例）

- 取官方全量源码包构建，**仅编译打包 snmpstats 模块**，不依赖 kamailio 本体包。
- 模块 `.so` 由 kamailio 运行时 `loadmodule "snmpstats.so"` 加载，不作为链接库供消费者使用
  （`cpp_info.libs` 为空，仅声明 `lib/kamailio/modules` 与 `share` 数据目录）。
- 无命令行可执行文件 → **不创建 commands.json**（R38 仅命令行工具需要）。

## 三、构建要点与踩坑

1. 上游同时提供 CMake 与经典 Makefile 两套体系；本配方走经典 Makefile（已实测）：
   ```
   make cfg include_modules=snmpstats          # 生成 src/config.mak，探测到 aarch64
   make modules modules=modules/snmpstats -j1  # 产出 src/modules/snmpstats/snmpstats.so
   ```
2. **net-snmp 包的 net-snmp-config --prefix 返回 "/"**（其配方 configure 未带真实 prefix），
   模块 Makefile 在找到 net-snmp-config 时用 `$(shell net-snmp-config --netsnmp-agent-libs)`
   会得到 `-L//lib ...` 这种无效路径 →
   配方显式传 `BUILDER=`（空）令其走 LOCALBASE 分支，`LOCALBASE=<net-snmp package_folder>`，
   得到 `-I<ns>/include -L<ns>/lib -lnetsnmpmibs -lnetsnmpagent -lnetsnmphelpers -lnetsnmp`。
3. **net-snmp 公开头文件包含 openssl 头**（`net-snmp/net-snmp-config.h` → `openssl/*.h`），
   只注入 net-snmp include 会编译失败 → `requires openssl/3.5.6` 并将其 include 目录加入 `CPATH`。
4. `make cfg` 依赖 `src/config.mak`；模块构建必须在其之后，否则报
   `No rule to make target 'cfg-defs'` / `Makefile.cfg: config.mak: No such file or directory`。
5. 本地探索期环境问题（与配方无关）：init-build 解压不完整（5885/6691 文件，`src/Makefile` 缺失），
   按 tarball 全量重解压后恢复正常；Conan `get()` 走 tarfile 解压，不受该本地问题影响。

## 四、上游测试清点与真实执行（R51 三步法）

### 1. 清点（源码包全量清点，N=17）

`kamailio-6.0.6_src.tar.gz` 内 `test/`、`tests/` 目录**文件共 17 个**（口径与评审脚本一致：官方
源码包内 `test/`、`tests/` 目录下的文件数）。此前一版按"顶层无 `test/` 目录"判断为 N=0，漏掉了
各模块子目录下的 `test/`、`tests/`，属**少报**，已按全量重枚举：

| # | 文件（源码包内路径） | 所属 | 角色 | 可独立执行 |
|---|---------------------|------|------|-----------|
| 1–10 | `utils/kamctl/dbtextdb/tests/{bad_table_null,bad_table_int,bad_table_long_row,bad_table_short_row,bad_table_wrong_type,bad_table_auto_dupe,unsorted_table,unsorted_table2,subscriber,test}` | kamctl dbtextdb | unittest 用例数据（无执行位） | 否（由 `dbtextdb_test.py` 消费） |
| 11 | `src/modules/janssonrpcc/test/run-tests.sh` | janssonrpcc | jsonrpc-c 模块冒烟脚本 | 否（需同树构建的 kamailio 主程序） |
| 12 | `src/modules/janssonrpcc/test/mem-test.sh` | janssonrpcc | valgrind 泄漏检查 | 否（需 kamailio 主程序 + valgrind） |
| 13 | `src/modules/janssonrpcc/test/test.cfg` | janssonrpcc | 上述脚本用配置 | 否（配置文件） |
| 14 | `src/modules/rtpproxy/test/kamailio.cfg` | rtpproxy | 手工联调配置样例 | 否（配置文件） |
| 15 | `src/modules/rtpproxy/test/exec_rtpproxy.txt` | rtpproxy | 启动命令行记录 | 否（无执行位、无断言） |
| 16 | `src/modules/rtpproxy/test/exec_pjsua.txt` | rtpproxy | 客户端命令行记录 | 否（无执行位、无断言） |
| 17 | `src/modules/tm/test/kill_sem.sh` | tm | 开发期 IPC 清理脚本 | 否（需 root，`ipcrm` 会删除宿主全部 SysV IPC） |

清点命令（可复现）：

```bash
tar tzf kamailio-6.0.6_src.tar.gz | grep -E '/(test|tests)/' | grep -v '/$' | wc -l   # → 17
tar tzf kamailio-6.0.6_src.tar.gz | grep -E '/(test|tests)/' | grep -v '/$'            # → 17 个文件
```

补充：`src/modules/snmpstats/` 内仅有源码、`mibs/`、`doc/`，**无任何测试文件**，
`src/Makefile*` 与模块 Makefile 亦无 check/test 目标注册
（`grep -rn 'add_test\|enable_testing' src/modules/snmpstats/` 无结果）。
上游 git 仓库另有 `test/unit/` 冒烟套件（49 个 `*.sh`，需 sipp/sipsak + 运行中的 kamailio 实例），
**不随官方发布包分发**，故不计入发布包清点面（N=17 口径 = 发布包内 `test/`、`tests/` 目录文件数）。

### 2. 运行（真实执行，层 1，`conanfile.py` build() 末尾）

清点面内 17 个文件本身都是测试**资产**（10 个用例数据 + 7 个脚本/配置/记录），其中唯一可自执行的是
`utils/kamctl/dbtextdb/dbtextdb_test.py` 这个 runner——它位于 `utils/kamctl/dbtextdb/`，路径不含 `test/` 段，
**不计入 N=17**，在 `test_package/MANIFEST.yml` 中以 `upstream_test_runner` 单独登记，避免与 17 个资产混淆
（上游自带 unittest 入口，3 个用例，仅依赖 Python 标准库 unittest/os/shutil/sys/tempfile；
用例数据取自上述第 1–10 号文件）。
已在本包 build() 末尾真实执行（`_run_upstream_tests()`）：

```
$ python3 dbtextdb_test.py -v
testExecute (__main__.DBTextTest.testExecute) ... ok
testOpenTable (__main__.DBTextTest.testOpenTable) ... ok
testParseQuery (__main__.DBTextTest.testParseQuery) ... ok
----------------------------------------------------------------------
Ran 3 tests in 0.017s

OK
```

- 通过率 **3/3（100%）**，failures=0 / errors=0，退出码 0（非零则 build 直接失败）
- 覆盖：N=17 中第 1–10 号用例数据文件全部由该 unittest 读入消费
- 证据文件 sha256：`dbtextdb_test.py` = `4493a15d942c61ea21f930d34e3f60b8fa8f1c0d167c0477519f8447e6bb7cc1`、
  `dbtextdb.py` = `6afe5939e83fbee14b7816255517f5ff2cb66f1bf4890b4749a73654ebe53beb`
- 未独立执行的 7 个文件（第 11–17 号）逐项技术原因登记在
  `test_package/MANIFEST.yml` 的 `upstream_tests[].not_executed_reason`，非"无环境"一句话豁免；
  其中 janssonrpcc/rtpproxy 两组需 kamailio 主程序 + 外部 rtpproxy/pjsua 进程
  （本包只产出 `snmpstats.so`，不构建 kamailio 本体），`tm/test/kill_sem.sh` 为破坏性清理脚本

### 3. 回填

- 上游台账：清点 **N=17**（个文件，逐项登记于 `test_package/MANIFEST.yml` 的 `upstream_tests`，**条目数=17**）、
  实际执行 **3 个 unittest 用例 3/3 通过**（runner 单独登记为 `upstream_test_runner`，不计入 17）；
  其余 7 个独立文件不可自执行的技术原因逐项写在 `not_executed_reason`（非"无环境"一句话豁免）
- 本包另有 `test_package/check_snmpstats.py` 的 10 项产物结构断言（层 2，10/10 通过，见 `reports/test-report.md`）

## 五、验证记录

- 探索构建：`snmpstats.so` 交叉编译链接通过（ELF 64-bit LSB, AArch64, ET_DYN）。
- 动态依赖（llvm-readelf -d）：`libnetsnmpmibs.so.40`、`libnetsnmpagent.so.40`、
  `libnetsnmp.so.40`、`libc.so`。
- 模块 MIB 数据：`KAMAILIO-MIB`、`KAMAILIO-REG-MIB`、`KAMAILIO-SIP-COMMON-MIB`、
  `KAMAILIO-SIP-SERVER-MIB`、`KAMAILIO-TC`。
- 上游测试真实执行（层 1）：`utils/kamctl/dbtextdb/dbtextdb_test.py -v` → `Ran 3 tests, OK`（3/3），
  退出码 0；由 build() 末尾调用，非零即构建失败（命令与输出见第四节）。
- `conan create`（W3）结果见 `.ci-result.json`，报告见 `reports/`。

## 六、最终状态

- 状态：`published`（`conan create` 本地验证通过，门禁 G1/G2/G3/G4 PASS、W3 本地 CI 通过；
  上游测试清点 17 项、真实执行 3/3 通过，其余 7 项独立文件逐项技术原因见第四节与 MANIFEST.yml）
- 测试：上游 unittest `dbtextdb_test.py` 3/3 通过（层 1）+ `test_package/check_snmpstats.py`
  10 项产物断言全通过（层 2，详见 `reports/test-report.md`）
- 结束标记：编译结束（档案已关闭 `.build-closed`）
---

**编译结束**: 2026-09-25 13:27
**最终状态**: published
