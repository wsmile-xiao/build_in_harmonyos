# Wiki 草稿 — Tcl 8.6.14 测试框架/工具链专项（PR !3200）

> 本稿为**测试框架/工具链专项**材料，与路径 B 知识条目（E215-draft-TCLB）**不重复计分**。
> 仅本地草稿；probe_only_no_upload，未 push、未 submit、未 /ai review。

## 1. tcltest 入口与测试范围

- 入口：`build-release/tcltest`（TCL_TEST 构建，含 testthread/drainEventQueue 测试命令）；
- 核心套件：`unix/tests/all.tcl`（152 个测试文件，Total 46635）；
- 包套件：`unix/pkgs/<pkg>/tests/all.tcl`；
- 排除规则：`Skipping test files that match: l.*.test`、`Only running test files that match: *.test`；
- 约束跳过：serverNeeded 1996 / win 472 / notRoot 253 / localeRegexp 100 / memory 85 /
  bigEndian 76 / emptyTest 62 / fullutf 58 / dde 49 / longIs32bit 47 / knownBug 42 等（共 3421）。

## 2. 工具链与构建环境

| 项 | 值 |
|---|---|
| Conan | 2.12.0 |
| Profile | ci/conan/profiles/ohos-aarch64（-pr:h / -pr:b 同 profile） |
| 编译器 | clang / clang++ 15.0.4，target aarch64-unknown-linux-ohos |
| 静态构建 | --disable-shared --enable-static（TCL_SHLIB_EXT=""，动态 load 不可用） |
| TMPDIR | /storage/Users/currentUser/tmp（hmdfs） |

## 3. 静态链接与 Thread/SQLite 注册方式

- 0010 `OhosStaticPkgs_Init`：`Sqlite3_Init` + `Tcl_StaticPackage(interp, "sqlite3", …)`、
  `Thread_Init` + `Tcl_StaticPackage(interp, "Thread", Thread_Init, NULL)`（0014 补上）；
- 静态桥接：`library/pkgIndex.tcl` → `package ifneeded Thread 2.8.9 [list load {} Thread]`
  （0013）；`pkgs/thread2.8.9/pkgIndex.tcl.in` 同步静态化（0015）；
- 子解释器（`interp create`）通过该桥接解析 `package require Thread`，避免
  worker 死亡 → 主线程 `vwait` 永久等待。

## 4. 本地门禁流程

- clean conan create：`conan create . -pr:h=…/ohos-aarch64 -pr:b=…/ohos-aarch64 --build=missing` → PASS；
- test_package：smoke 6/6 + C API 4/4 = 10/10 → PASS；
- conan-verify：G1/G0/G2/G3 全 PASS；
- W3 本地 CI：`ci/conan/build_and_test.sh archives/t/tcl/8.6.14`（CI_PACKAGES 定向）→
  L0/L1/L2/L4/L5 全 PASS，Success 1 / Failed 0，生成 ci-metadata.json；
- finish：Step3.5 W3 使用 run_local_ci 固定 600s 超时，而 build_and_test.sh 声明
  60 分钟超时（含全量 conan create + make test），本地 600s 必然超时 —— 属工具链
  超时窗口限制，非 PR 代码问题；W3 完整时限运行已 PASS。

## 5. 真实测试统计

### 核心套件（all.tcl 口径）

| 运行 | Total | Passed | Skipped | Failed |
|---|---|---|---|---|
| 当前 PR（0010–0015） | 46635 | 43191 | 3421 | 23* |
| pristine 上游 | 46635 | 42996 | 3616 | 23* |

\* all.tcl 汇总口径 Failed=23；逐 test case 审计为 **24 个失败用例 / 9 个文件**
（cmdAH.test 含文件级错误 "couldn't open /tmp/touch.me"，未计入 all.tcl Failed 汇总）。

失败分类：A 类（上游基线平台限制）10 项、C 类（环境/依赖/配置）14 项、
B 类（PR 回归）0 项、D 类（可补丁）0 项。pristine 与 PR 失败集合一致 → 0010–0015 未引入回归。

### 包套件

| 套件 | Total | Passed | Skipped | Failed | rc |
|---|---|---|---|---|---|
| Thread 核心 unix/tests/thread.test | 52 | 50 | 2 | 0 | 0 |
| Thread 2.8.9 | 138 | 122 | 16 | 0 | 0 |
| sqlite3.44.2 | 1 | 1 | 0 | 0 | 0 |
| itcl4.2.4 | 0 | 0 | 0 | 0 | 0 |
| tdbc1.1.7 | 0 | 0 | 0 | 0 | 0 |
| tdbc::sqlite3 | 0 | 0 | 0 | 0 | 0 |

### 失败/跳过原因

- Thread 2.8.9 16 skipped：平台/环境约束（unthreaded、win、serverNeeded 等）；
- Itcl/tdbc/tdbc::sqlite3 **Total=0 仅由静态构建动态加载不可用导致**：
  TCLLIBPATH 环境下报 "dynamic loading is not currently available on this system"；
  tdbcsqlite3 的 `library/tdbcsqlite3.tcl` 存在且 pkgIndex 引用正确，但依赖 tdbc
  动态加载失败 → Total=0（未标为 PASS，按真实统计记录）。

## 6. 复用范围与限制条件

- 可复用：OHOS aarch64 静态构建 Tcl 8.6.14 的门禁流程、包套件统计口径、
  Thread 静态包注册模式（0013–0015）；
- 限制：Itcl/tdbc/tdbcsqlite3 依赖动态加载，静态构建下套件不可运行（Total=0）；
  核心 24 失败中 10 项为平台限制、14 项为环境限制，不可在静态构建内修复；
  已知系统差异（/tmp 只读、HMDFS ln -sf、ELF 签名、仅有 clang、SELinux、
  setreuid/chroot 内核裁剪）不作为新的 HarmonyOS 系统差异专项申报。
