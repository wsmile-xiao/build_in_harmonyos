# 测试报告 — libhbalinux 1.0.16

- 目标平台：OpenHarmony / HarmonyOS PC aarch64（OHOS SDK 26.0.0.18，clang 15.0.4）
- Profile：`ci/conan/profiles/ohos-aarch64`（os=OHOS 6.0 / armv8 / clang 15 / libc++ / cppstd 17 / Release）
- 报告生成：2026-09-22（本机构建机）
- 结论：上游**无自动化测试、无样例程序**（如实申报）；本包可执行验证面 = `test_package`（11/11 通过，其中 OHOS 专属 3 条）
  + W3 本地 CI 模拟（L0/L1/L1e/L4/L5 全通过，JC/KC 全通过，成功 1/1）
  + staging 验证（DESTDIR 安装后从 staging 前缀 dlopen 并调用真实入口）

## 1. 上游测试入口核验（R51 三步法，真实命令 + 退出码）

| # | 命令 | 退出码 | 原始输出 |
|---|------|--------|----------|
| 1 | `tar tzf libhbalinux_1.0.16.orig.tar.gz` | 0 | 28 条目录项（1 目录 + 27 文件），**无** `test/`、`tests/`、`CHANGELOG`、`NEWS` |
| 2 | `grep -nE 'TESTS\|check_PROGRAMS\|check-local\|BUILD_TESTING\|pytest' Makefile.am configure.ac` | **1** | 无匹配（Makefile.am 仅 `lib_LTLIBRARIES`/`pkgconfig_DATA`/`install-data-hook`） |
| 3 | `ls -d tests test` | **1** | `No such file or directory` |
| 4 | `make check` | — | 目标不存在（Makefile.am 未定义 check 目标） |
| 5 | `cat Makefile.am`（全文 35 行） | 0 | 无任何 `TESTS`/`check_PROGRAMS` 变量 |

**上游用例总数：0**。SNIA 的示例程序（`hbaapitest.c`/`hbasample.c`）属于 **libHBAAPI** 工程，
不随 libhbalinux tarball 发布（`libhbaapi/2.2.9` 已单独适配并执行留证）。
⇒ 不存在"漏测的上游案例"；不以下游 test_package 冒充上游测试统计。

### 上游唯一可执行路径（已真实执行并留证）

`Makefile.am:16-33` 的 `install-data-hook`：安装期把 vendor 库路径追加到 `${sysconfdir}/hba.conf`。
OHOS 上 `/etc` 只读且无该文件，上游脚本自身容错：

```
$ make install DESTDIR=<staging>            # rc=0
** WARNING: //etc/hba.conf does not exist
** system configuration not updated
```
日志：`reports/staging-verify.log`、`reports/w3-local-ci.log:410`

## 2. test_package 消费者测试（11 条断言，真实 API 调用）

执行方式：`conan create archives/l/libhbalinux/1.0.16 -pr:h/-pr:b=ci/conan/profiles/ohos-aarch64 --build=libhbalinux/1.0.16`
→ test_package 内 `cmake build` + `self.run(<binary>, env="conanrun")`。

| 用例 | 断言 | 结果 |
|------|------|------|
| case1 | `HBA_RegisterLibraryV2()` 返回 `HBA_STATUS_OK` 且填回 5 个关键 handler | PASS |
| case2 | `GetVersionHandler() == HBA_LIBVERSION`(2) | PASS |
| case3 | `LoadLibraryHandler() == HBA_STATUS_OK`（adapter_init 扫 sysfs） | PASS |
| case4 | 无 `/sys/class/fc_host` 时适配器计数为 0 | PASS |
| case5 | `GetAdapterNameHandler(0)` 越界被拒（实测返回 6 = `HBA_STATUS_ERROR_ILLEGAL_INDEX`） | PASS |
| case6 | `OpenAdapterHandler("hba0")` 返回无效句柄 0 | PASS |
| case7 | `FreeLibraryHandler() == HBA_STATUS_OK` | PASS |
| case8 | **[OHOS]** `dlopen("libhbalinux.so.2")` 成功 | PASS |
| case8b | **[OHOS]** dlopen 得到的 DSO 导出 `HBA_RegisterLibraryV2` | PASS |
| case9 | **[OHOS]** 无 fc_host sysfs 树时不虚报适配器 | PASS |
| case10 | v1 入口 `HBA_RegisterLibrary()` 仍可用 | PASS |

```
== result: 11 passed, 0 failed, 0 skipped ==
```
原始输出：`reports/w3-local-ci.log:513-527`

**鸿蒙专属用例：3 条**（case8/case8b/case9），均针对 OHOS 平台事实（DSO dlopen 契约、无 FC sysfs 树）。

## 3. W3 本地 CI 模拟（ci/conan/build_and_test.sh，作用域 = 本 PR 10 个文件）

| 门禁 | 结果 | 关键原始输出 |
|------|------|--------------|
| G0e 根目录白名单 | pass | `[ok] G0e: Root directory whitelist passed` |
| L0i 依赖已发布（R36） | pass | `[ok] dependency in registry: automake/1.18 / libhbaapi/2.2.9 / libpciaccess/0.19 / libtool/2.5.4 / zlib/1.3.1.2` |
| L0j 版本冲突（R37） | pass | `[ok] version not in registry yet (first publish)` |
| L0k commands.json（R38） | pass | `[ok] library package, commands.json not required` |
| L0m 目录结构 | pass | `[ok] L0m: directory structure valid` |
| KC1-KC5 知识库质量 | pass | `KC_RESULT=pass KC_ERRORS=0`（540 kv，index 一致） |
| JC1-JC6 杂项文件 | pass | `检查模式: prdiff (10 个文件)`；`JC6: 涉及软件数: 1（合规）`；`Junk Files: 0` |
| L1 / L1a / L1b | pass | `test_package was executed by conan create` + `Test execution evidence found in log` |
| L1e 破坏性反向验证（R34） | pass | `[ok] L1e: Negative test confirmed — test genuinely depends on libhbalinux`（把 lib/ 移走后测试确实失败） |
| L4 补丁危险函数扫描 | pass | `[ok] L4: patches clean`（本包补丁数 0） |
| L5 产物基线 | pass | `[ok] L5: lib/ has content (library package)` |
| 构建汇总 | **1/1 成功** | `Pass rate: 100.0% (1/1)` |

`.ci-result.json`（由 finish 写入，非手写）：`exit_code: 0`，`integrity_hash=e2a78e28f2ce9d6`（截断显示见文件），
`log_sha256=9d50c9654d2a7834cf5bf55e56e855cf7767f925a8ef1026710fd2d91121bede`

## 4. staging 验证（库包等价物：DESTDIR 安装 + 从 staging 前缀加载）

```
$ ./bootstrap.sh                                                     rc=0
$ sed -i 's/umask 077/umask 022/g' configure                          # E011
$ ./configure --build=aarch64-unknown-linux-gnu --host=aarch64-linux-ohos --prefix=/   rc=0
$ make -j2                                                           rc=0
$ make install DESTDIR=<staging>                                     rc=0
--- staging 前缀 ---
<STAGE>/lib/libhbalinux.so.2.0.2 / .so.2 / .so / libhbalinux.a / libhbalinux.la
<STAGE>/lib/pkgconfig/libhbalinux.pc
--- 从 staging 前缀加载 ---
staging dlopen OK; RegisterLibraryV2 rc=0; GetVersionHandler=0x5a59ecbe7c; version=2
probe run rc=0
```
日志：`reports/staging-verify.log`；标记：`.staging-verified`

## 5. 日志路径清单

| 日志 | 内容 |
|------|------|
| `archives/l/libhbalinux/1.0.16/reports/w3-local-ci.log` | W3 本地 CI 全量输出（L0/L1/L1e/L4/L5、KC、JC、11 条断言原文） |
| `archives/l/libhbalinux/1.0.16/reports/conan-create.log` | G2 干净构建日志（configure/make/test_package） |
| `archives/l/libhbalinux/1.0.16/reports/conan-verify-report.md` | G0-G4 + L2/L4/L5 结论 |
| `archives/l/libhbalinux/1.0.16/reports/staging-verify.log` | staging 安装 + 从 staging 前缀 dlopen 验证 |
| `archives/l/libhbalinux/1.0.16/.ci-result.json` | W3 结果（exit_code/integrity_hash/log_sha256，finish 生成） |
| `$TMPDIR/builds/libhbalinux-1.0.16-logs/` | 本机探索/构建全量日志（含首次错误 01_bootstrap、02_configure、05_make 等） |

## 6. 已知非阻塞项（非本包文件、非本包缺陷）

| 项 | 现象 | 归属 |
|----|------|------|
| G0 干净构建验证失败 | `configure` 直接运行于解包目录（无 conan 依赖环境）→ 期望失败；属非阻塞步骤 | 框架步骤（本包 configure 需要 pciaccess/HBAAPI 的 pc 文件与 conan 环境，见 conan-verify G2 已 PASS） |
| graph validate 报 `E305.kv: rec_approach 为空` | 全仓知识库既有条目 | 框架/知识库 |
| `check_knowledge_completeness` 报 1396 条待审草稿 | 全仓既有草稿积压 | 框架/知识库 |
| `gen_summary` 失败：`'str' object has no attribute 'append'` | SUMMARY.md 未刷新 | 框架脚本缺陷 |
| `refresh-patch --auto` 在基线目录写入 0 字节占位文件并生成 12 个"生成文件"补丁 | 已删除该 12 个补丁并从 tarball 重建 pristine 基线；本包 `patches/` 保持 0 个 | 框架脚本缺陷（会破坏后续 autoreconf，见 notes.md 问题 8） |
