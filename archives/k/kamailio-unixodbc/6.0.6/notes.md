# kamailio-unixodbc 6.0.6 适配笔记

## 一、基本信息

| 项 | 值 |
|----|----|
| 上游 | kamailio 6.0.6 |
| 源码 | https://www.kamailio.org/pub/kamailio/6.0.6/src/kamailio-6.0.6_src.tar.gz |
| sha256 | `32e4290c6813c9d0289abe9ec2de9138e12e0381179218a7fed374ad813ecc48` |
| 构建体系 | kamailio 经典 Makefile 体系（src/Makefile + Makefile.defs + Makefile.modules） |
| 打包产物 | `db_unixodbc.so`（unixODBC 数据库连接器模块，260,416 bytes） |
| 平台目标 | OHOS / aarch64（SDK clang 默认 target 即 aarch64-unknown-linux-ohos） |
| 依赖 | unixodbc/2.3.12 |

## 二、打包口径（参照 archives/k/kamailio-snmpstats/6.0.6 同族先例）

- 取官方全量源码包构建，**仅编译打包 db_unixodbc 模块**，不依赖 kamailio 本体包。
- 模块 `.so` 由 kamailio 运行时 `loadmodule "db_unixodbc.so"` 加载，不作为链接库供消费者使用
  （`cpp_info.libs` 为空，仅声明 `lib/kamailio/modules` 模块目录）。
- 无命令行可执行文件 → **不创建 commands.json**（R38 仅命令行工具需要）。

## 三、构建要点与踩坑

1. 上游同时提供 CMake 与经典 Makefile 两套体系；本配方走经典 Makefile（已实测）：
   ```
   make cfg include_modules=db_unixodbc                       # 生成 src/config.mak，探测到 aarch64
   make modules modules=modules/db_unixodbc -j1               # 产出 src/modules/db_unixodbc/db_unixodbc.so
   ```
2. **模块 Makefile 的 ODBC 探测必须钉死到 LOCALBASE 分支**。`src/modules/db_unixodbc/Makefile`：
   ```
   ifeq ($(CROSS_COMPILE),)
   ODBCCFG=$(shell which odbc_config)
   endif
   ifneq ($(ODBCCFG),)
   # 用 odbc_config --cflags/--libs（宿主路径）
   else
   DEFS += -I$(LOCALBASE)/include ; LIBS += -L$(LOCALBASE)/lib -lodbc   # ← 需要的分支
   ```
   conan 的 unixodbc 包**不含 `bin/odbc_config`**，看似天然走回退分支；但只要构建机 PATH 里
   存在系统 `odbc_config`（发行版 unixODBC 的常见布局），`which` 就会命中并注入宿主 include/lib
   路径 → 交叉编译产物指向宿主库。故配方显式传 **`ODBCCFG=`**（make 命令行变量优先级高于
   Makefile 内部赋值）把分支钉死，并以 `LOCALBASE=<unixodbc package_folder>` 提供正确路径。
   （与 snmpstats 用 `BUILDER=` 空值把 net-snmp-config 分支钉死是同一手法。）
3. 依赖注入只走 `Environment`（CC/CPATH/LIBRARY_PATH）+ make 变量，未向任何共享系统前缀写入
   路径（R49 口径）；`unixodbc` 的 include/lib 直接取自其 package_folder。
4. `make cfg` 依赖 `src/config.mak`；模块构建必须在其之后，否则报
   `No rule to make target 'cfg-defs'` / `Makefile.cfg: config.mak: No such file or directory`。
5. 本地探索期环境问题（与配方无关，同 snmpstats）：init-build 从 kamailio.org 断点下载被工具超时
   中断；复用同源同 sha256 的已缓存 tarball（`$HOME/tmp/builds/…tar.gz`，sha256 校验一致）后正常。

## 四、上游测试清点与真实执行（R51 三步法）

### 1. 清点（源码包文档级全量清点，N=17）

`kamailio-6.0.6_src.tar.gz` 内 `test/`、`tests/` 目录共 **4 个、文件共 17 个**（此前申报 N=0
仅按"顶层无 test/ 目录"判断，漏掉了各子目录下的 test/tests，属少报，已按全量重枚举）：

| # | 文件（源码包内路径） | 所属 | 角色 | 可独立执行 |
|---|---------------------|------|------|-----------|
| 1–10 | `utils/kamctl/dbtextdb/tests/{bad_table_null,bad_table_int,bad_table_long_row,bad_table_short_row,bad_table_wrong_type,bad_table_auto_dupe,unsorted_table,unsorted_table2,subscriber,test}` | kamctl dbtextdb | unittest 用例数据（无执行位） | 否（由 11 号脚本 `dbtextdb_test.py` 消费） |
| 11 | `src/modules/janssonrpcc/test/run-tests.sh` | janssonrpcc | jsonrpc-c 模块冒烟脚本 | 否（需同树构建的 kamailio 主程序） |
| 12 | `src/modules/janssonrpcc/test/mem-test.sh` | janssonrpcc | valgrind 泄漏检查 | 否（需 kamailio 主程序 + valgrind） |
| 13 | `src/modules/janssonrpcc/test/test.cfg` | janssonrpcc | 上述脚本用配置 | 否（配置文件） |
| 14 | `src/modules/rtpproxy/test/kamailio.cfg` | rtpproxy | 手工联调配置样例 | 否（配置文件） |
| 15 | `src/modules/rtpproxy/test/exec_rtpproxy.txt` | rtpproxy | 启动命令行记录 | 否（无执行位、无断言） |
| 16 | `src/modules/rtpproxy/test/exec_pjsua.txt` | rtpproxy | 客户端命令行记录 | 否（无执行位、无断言） |
| 17 | `src/modules/tm/test/kill_sem.sh` | tm | 开发期 IPC 清理脚本 | 否（需 root，`ipcrm` 会删除宿主全部 SysV IPC） |

清点命令（可复现）：

```bash
tar tzvf kamailio-6.0.6_src.tar.gz | grep -E '(^|/)(test|tests)/' | wc -l   # → 17
tar tzvf kamailio-6.0.6_src.tar.gz | grep -E '(^|/)(test|tests)/'            # → 4 个目录 + 17 个文件
```

补充：`src/modules/db_unixodbc/` 内仅有源码与 `doc/`，无测试源文件，也无
check / ctest 目标注册（`grep -rl 'add_test\|enable_testing' src/modules/db_unixodbc/` 无结果；
`src/Makefile*` 无 check/test 目标）。上游 **git 仓库另有** `test/unit/` 冒烟套件
（49 个 `*.sh`，需 sipp/sipsak + 运行中的 kamailio 实例），**不随官方发布包分发**，
故不计入发布包清点面（N=17 口径 = 发布包内 test/tests 目录文件数）。

### 2. 运行（真实执行，层 1 门禁，`conanfile.py` build() 末尾）

17 个文件中唯一自包含、无需运行中 kamailio 实例的上游测试是
`utils/kamctl/dbtextdb/dbtextdb_test.py`（上游自带 unittest 入口，3 个用例，
仅依赖 Python 标准库 time/unittest/fcntl/os/shutil/sys/tempfile）。已在本包 build() 末尾真实执行：

```
$ python3 dbtextdb_test.py -v
testExecute (__main__.DBTextTest.testExecute) ... ok
testOpenTable (__main__.DBTextTest.testOpenTable) ... ok
testParseQuery (__main__.DBTextTest.testParseQuery) ... ok
----------------------------------------------------------------------
Ran 3 tests in 0.013s

OK
```

- 通过率 **3/3（100%）**，failures=0 / errors=0；退出码 0（非零则 build 失败）
- 证据文件 sha256：`dbtextdb_test.py` = `4493a15d942c61ea21f930d34e3f60b8fa8f1c0d167c0477519f8447e6bb7cc1`、
  `dbtextdb.py` = `6afe5939e83fbee14b7816255517f5ff2cb66f1bf4890b4749a73654ebe53beb`
- 未执行的 14 项逐项技术原因已登记在 `test_package/MANIFEST.yml`
  （`upstream_tests[].not_executed_reason`），非"无环境"一句话豁免

### 3. 回填

- 上游台账：清点 N=17、实测执行 N′=3、通过率 3/3（100%）、未执行 14（逐项技术原因）
- 本包另有 `test_package/check_db_unixodbc.py` 的 10 项产物结构断言（10/10 通过，
  见 `reports/test-report.md`），作为消费者视角（层 2）验证

## 五、验证记录

- 探索构建：`db_unixodbc.so` 交叉编译链接通过（ELF 64-bit LSB, AArch64, ET_DYN）。
- 动态依赖（`llvm-readelf -d`）：`libodbc.so.2`、`libc.so`。
- **无 RPATH/RUNPATH**：动态段不含构建机/缓存库路径（运行时依赖由 Conan 或 LD_LIBRARY_PATH 解析）。
  注意产物**未 strip**，调试信息字符串中仍留有构建目录绝对路径（如
  `…/.conan2/p/b/kamaif9aa97865ef77/b/src/src/modules/db_unixodbc`，`strings` 实测 3 处）——
  属调试符号引用，与动态链接解析无关（`llvm-readelf -d` 已确认无 RPATH/RUNPATH）。
- 打包口径与同族 precedent 一致：`package_type = "shared-library"`（Kamailio 模块为可加载共享对象，
  与 `archives/k/kamailio-snmpstats/6.0.6/conanfile.py` 同款声明）。
- 模块 API 符号：`db_bind_api`（向 kamailio core 注册的 DB 连接器 API，见 `db_unixodbc.c` exports）。
- 上游测试真实执行（层 1）：`utils/kamctl/dbtextdb/dbtextdb_test.py -v` → `Ran 3 tests, OK`（3/3），
  退出码 0；由 build() 调用，非零即构建失败（命令与输出见第四节）。
- `conan create`（W3）结果见 `.ci-result.json`，报告见 `reports/`。

## 六、流程观察（W3 阻塞项的根因，供 SKILL 迭代参考）

本次 `finish` 首次运行时 W3 被 junk_check 拦下，报 `archives/c/cloog/0.21.1/.build-closed`、
`archives/c/cloog/0.21.1/.staging-verified`、`archives/k/kics/2.1.20/.staging-verified`
三个"未登记隐藏文件"——**均非本包文件，且均为 main 上他人 PR 已跟踪的存量文件**
（`git ls-files` 确认为 tracked，来源提交 `906cc59ae7`（cloog）等）。

根因链：`ci/scripts/junk_check.sh` 的检查范围选择为
prdiff（`pr.diff`）→ incremental（`git diff origin/main...HEAD`）→ full（`git ls-files` 整仓）。
本地在 finish 阶段尚未提交任何东西，`origin/main...HEAD` 为空 → 退回 **full 整仓扫描** →
命中他包存量垃圾 → 本包 W3 被阻塞。CI 侧走 prdiff（PR 文件清单）不受影响。

处置：仅把本包 7 个文件提交到任务分支（使增量 diff 非空、模式回到 incremental）后重跑 finish，
未改动他包任何文件（W2 原子性）。

## 七、W4 Pre-PR 独立审计记录

- 执行方式：`pre_pr_audit.py generate` 生成输入 → 独立子任务（隔离上下文）按 `.gitcode/code-style.md`
  与 `.gitcode/review-memory.md` 逐条审查 8 个变更文件 → 结论落 `reports/audit-result.json`
- 结论：**PASS**（P0=0、P1=0、P2=1、P3=2）
- P2 已修复：原表述「产物不内嵌构建机/缓存路径」不准确——实测产物 `not stripped`，
  debug 字符串含缓存绝对路径（见第五节，已收紧为「动态段无 RPATH/RUNPATH」+ 补充未 strip 事实）
- P3 处置（不阻塞，保留）：
  1. `package_type = "shared-library"`——与同族 `kamailio-snmpstats/6.0.6` 同款声明，语义正确（可加载模块）
  2. `compilers.get("c") or "clang"` 回退——与同族先例写法一致；CI profile `ohos-aarch64` 已显式提供
     `tools.build:compiler_executables={"c": "/data/service/hnp/bin/clang", ...}`，回退分支在 CI 不触发

## 八、最终状态

- 状态：`published`（`conan create` 本地验证通过，门禁 G1/G2/G3/G4 PASS、W3 本地 CI 通过；
  上游测试清点 17 项、真实执行 3/3 通过，其余 14 项逐项技术原因见第四节与 MANIFEST.yml）
- 测试：上游 unittest `dbtextdb_test.py` 3/3 通过（层 1）+ `test_package/check_db_unixodbc.py` 10 项产物断言全通过（层 2，详见 `reports/test-report.md`）
- 结束标记：编译结束（档案已关闭 `.build-closed`）
---

**编译结束**: 2026-09-25 14:47
**最终状态**: published
