# libgtop 2.41.3 适配笔记

**生成日期**: 2026-09-09
**任务**: libgtop-2.41.3-r01-pc3-10-20260909T123830Z（高难度挑战）
**Wiki 上游**: https://gitlab.gnome.org/GNOME/libgtop
**源码**: https://download.gnome.org/sources/libgtop/2.41/libgtop-2.41.3.tar.xz
**SHA-256**: 775676df958e2ea2452f7568f28b2ea581063d312773dd5c0b7624c1b9b2da8c

---

## 编译环境

- 构建系统: autotools (configure.ac + Makefile.am)
- 编译器: clang 15（OHOS SDK 26.0.0.18，aarch64）
- 平台: HarmonyOS PC / OHOS 6.0 (aarch64, armv8)
- conan: 2.29.1（OHOS 适配版），profile ci/conan/profiles/ohos-aarch64
- 依赖: glib/2.84.0.1（provy proxy-libintl 的 libintl，glib 包内自带 libintl.so）
- 分支: feat/libgtop-2.41.3，worktree /storage/Users/currentUser/junshi_liu/worktrees/pc3-10-libgtop-2.41.3

## 关键适配点

1. **config.status tmpdir umask 077 → 022**（patches/0001-configure-umask-022.patch）：
   setgid HMDFS 下 umask 077 生成的临时目录不可写，config.status 报
   `./confXXXXXX/subs1.awk: Permission denied`。与 a52dec 同根因，同修复。

2. **g_libintl_ngettext 链接**：glib 包的 libintl.h 把 `ngettext` 宏映射为
   `g_libintl_ngettext`（glib 内嵌 proxy-libintl 命名），OHOS libc 无 libintl。
   src/daemon 与 libgtop-2.0 静态库引用该符号，需 `-L<glib libdir> -lintl`
   链接；conftest 运行期还需 `-Wl,-rpath,<glib libdir>` 定位 libintl.so.8。
   package_info.libs 增补 `intl`，使生成 libgtop-2.0.pc 的 Libs 携带 -lintl。

3. **MAKEINFO=true**：CI 无 texinfo，doc/ 的 libgtop2.info 生成失败，注入
   MAKEINFO=true 跳过（手册非交付物，库/头文件/pc 位交付内容）。

4. **OHOS 内核 uname**：`release HongMeng Kernel 1.12.0` 无法解析为内核版本号，
   libgtop 仅打 WARNING（version code 0），不阻塞运行。

5. **NLS 禁用**（--disable-nls）：OHOS 无完整 gettext 生态，禁用 NLS 避免
   libintl 依赖扩散；glib 头文件映射的 g_libintl_* 仍由 -lintl 提供。

6. **mountlist 回退 /proc/self/mounts**（patches/0002-mountlist-proc-self-mounts.patch）：
   OHOS/容器系统无 /etc/mtab，libgtop 的 setmntent(MOUNTED) 打开失败导致
   mountlist 恒为空；回退读取 /proc/self/mounts（始终存在，反映真实挂载）。
   实测后 mountlist 枚举 139 个挂载点（首挂载 "/"）。

## HarmonyOS 专项测试

test_package/ohos_platform_test.c（随 test_package 编译运行，5 断言全部通过）：

| 断言 | 公开 API | 结果 |
|---|---|---|
| 进程表枚举 | glibtop_get_proclist | OK: 173 processes |
| 进程状态（自身） | glibtop_get_proc_state(getpid()) | OK: uid=20020101 state=1 |
| 系统信息 | glibtop_get_sysinfo | OK: ncpu=20 |
| 网络设备 | glibtop_get_netlist | OK: 13 devices (first=lo) |
| 挂载点 | glibtop_get_mountlist(all_fs=1) | OK: 139 mounts (first=/) |

平台差异记录：OHOS 普通用户无法读 /proc/1/stat 等系统进程（Permission denied），
专项测试用 getpid() 自身进程验证（上游示例同样读取自身）。

## W2/W3 基线隔离复验（baseline_isolation_audit）

W3/finish 的 JC5 全仓扫描命中了其他库（util-linux-login）既有基线文件
`archives/u/util-linux-login/2.42.2/.ci-trigger`（main 历史存在、git tracked、
0 字节）。按基线隔离规则处理，逐项记录：

| 字段 | 值 |
|---|---|
| path | archives/u/util-linux-login/2.42.2/.ci-trigger |
| pre_sha256 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855（空文件）|
| isolation_command | `mv archives/u/util-linux-login/2.42.2/.ci-trigger archives/u/util-linux-login/2.42.2/.ci-trigger.isolated` |
| rerun_command | `python3 scripts/ohc-run.py finish libgtop 2.41.3 published`（带 pr.diff 走 prdiff 模式）|
| rerun_exit_code | 0（finish_success）|
| restore_command | `mv archives/u/util-linux-login/2.42.2/.ci-trigger.isolated archives/u/util-linux-login/2.42.2/.ci-trigger` |
| post_sha256 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |

**pre_sha256 == post_sha256 确认**：是（e3b0c442…855）。
当前库 diff/staged/PR 未包含该路径：确认（`git status` 对 util-linux-login 0 命中；
libgtop 交付路径仅 archives/l/libgtop/）。
隔离说明：本机未 commit 前 junk_check 回退 full 模式用 `git ls-files` 全仓扫描
才误报其他库基线；真实 CI 用 PR diff（prdiff 模式）只扫当前库交付文件，不含
该基线文件。未修改、未提交、未写入知识库或 PR 该基线文件。

## W3 门禁结果

- ohc-run.py finish libgtop 2.41.3 published → exit 0（finish_success；manifest 状态为 built，制品未上传远端制品仓）
- W2 结构检查（L0a-L0e）、R36 依赖检查（glib/2.84.0.1 已发布）、conan create
  编译验证（W3）全部通过；`.ci-result.json` 已由 finish 自动写入（含日志 SHA-256）。
- commands.json（R38）：archives/l/libgtop/commands.json 已声明 libgtop_server2/
  libgtop_daemon2（libexec daemons），随 PR 提交。两 daemon 安装于 libexec/
  （非 bin/，不入 PATH）；conan DESTDIR 打包跳过了上游 install-exec-hook 的
  chown root/chmod 4755（包内权限 770，未设置 setuid 位），库消费者不受影响。

## 知识候选台账（knowledge_candidate_ledger）

| # | 候选（非噪声） | 真实错误 | 根因 | 修复 | 验证 | 适用范围 | 正式知识查重 | 图谱查重 | 草稿查重 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | config.status umask 077→022 | `config.status: ./confXXXXXX/subs1.awk: Permission denied` | HMDFS setgid 下 umask 077 目录当前进程不可写 | patches/0001 改 configure umask 022 | finish W3 通过 | 所有 autotools 配置期 | **E011 完全覆盖（reuse_existing）** | E011.kv 覆盖 | 无 |
| 2 | g_libintl_ngettext 链接缺失 | `ld.lld: undefined symbol: g_libintl_ngettext` | glib 包 libintl.h 把 ngettext 宏映射为 g_libintl_ngettext；OHOS libc 无 libintl；需链 conan glib 包内 libintl.so | 配方注入 `LDFLAGS=-L<glib> -lintl -Wl,-rpath` + package_info.libs 增补 intl | conan create + test_package 通过 | 任何 autotools 消费者链 glib 静态库 | E015/E027/E107/E123/E142 为**链接期 libintl 族**（部分覆盖，无 conan glib 内置 libintl.so + autotools rpath 注入先例） | 图谱同族条目链接期 | **DRAFT-libgtop-glib-libintl-link 新建（new_draft）** |
| 3 | MAKEINFO=true | `make[3]: *** [doc/libgtop2.info] Error 127：makeinfo: command not found` | CI 无 texinfo，doc/ 手册生成失败 | 配方注入 MAKEINFO=true | finish W3 通过 | 所有 autotools 库 doc/ 含 .texi | 未命中 | 未命中 | **DRAFT-libgtop-makeinfo-missing 新建（new_draft）** |
| 4 | mountlist 回退 /proc/self/mounts | `Could not open /etc/mtab`，mountlist 空（0 挂载点） | OHOS/容器无 /etc/mtab，setmntent(MOUNTED) 失败 | patches/0002 回退 /proc/self/mounts | 鸿蒙专项测试 139 mounts | 所有读 /etc/mtab 的库（OHOS/容器） | 未命中 | 未命中 | **DRAFT-libgtop-mountlist-mtab-fallback 新建（new_draft）** |

**七轴查重（候选 2/3/4 相对既有条目）**：
- exact_duplicate：否（3 项均与既有条目构成 trigger 或场景差异）
- causal_duplicate：否——候选 3/4 无既有原因链；候选 2 与 E107 共享 libintl 缺失根因但
  场景为 conan glib 内置 libintl.so + autotools rpath，属增量
- trigger_overlap：候选 2 与 E015/E027/E107/E123/E142 共 trigger（libintl 链接）；
  候选 3/4 无重叠
- solution_overlap：候选 2 的 rpath + -lintl 注入方案与 E107（中间库）不同；
  候选 3/4 无既有方案
- combination_novelty：是——候选 3/4 全新增；候选 2 是 autotools+conan-glib 组合增量
- boundary_novelty：是——OHOS 无 /etc/mtab、无 texinfo 属边界条件
- test_migration_novelty：是——候选 4 由鸿蒙专项测试验证（mountlist 139 挂载点）

**路径判定**：候选 1 完整重复 E011 → reuse_existing，走路径 A（无独立草稿）；
候选 2/3/4 已验证、可跨库复用且查重未命中/部分覆盖 → **路径 B，new_draft**
（3 个同 stem 草稿对随本 PR 提交）。任务前缀仍为【高难度挑战】。

## 构建命令

```bash
cd archives/l/libgtop/2.41.3
conan create . \
  -pr:h=<worktree>/ci/conan/profiles/ohos-aarch64 \
  -pr:b=<worktree>/ci/conan/profiles/ohos-aarch64
```

结果：conan create 全绿，test_package 消费者用例编译、链接、运行通过
（consumer 经公开 API glibtop_init/get_cpu/get_mem/get_uptime/glibtop_close）。

## 上游测试台账（完整枚举）

口径结论：**libgtop 2.41.3 官方源码无独立上游测试套件**。
逐项证据：

| 分类 | 入口 | 独立上游用例? | 依据 |
|---|---|---|---|
| 测试目录 | tests/ 目录 | 无 | 源码树无任何 tests/ 目录 |
| 测试目标 | TESTS / check_PROGRAMS / check-local | 无 | 所有 Makefile.am 无 TESTS/check_PROGRAMS/check-local；`make check` 的目标不存在 |
| 测试框架 | TEST_CASE / gtest / catch2 / CppUnit | 无 | 全树无 TEST_CASE/gtest/catch2/CPPUNIT 引用 |
| 测试脚本 | test*.sh / test*.pl | 无 | 全树无测试脚本（m4/progtest.m4 为 autotools 内部宏） |
| 框架头/源码 | include/glibtop/*.h, sysdeps/*.c | 无 | 头文件与 sysdeps 为库实现，非用户测试 |
| 样例/示例 | examples/ 下 19 个 noinst_PROGRAMS | 否（样例，不计入独立用例） | noinst_PROGRAMS 示例程序，API 演示用途 |
| 基准 | benchmarks | 无 | 无基准目录 |
| fixture | 无 | 无 | 无 fixture 文件 |

**双口径统计**：
- source_declared_total = 0（官方 tag 源码中无可复制枚举的独立测试用例声明）
- configured_executable_total = 0（无测试目标被实例化/注册）
- executed_passed_total = 0
- 样例程序（不计入上游用例，仅作 API 运行验证）19 个全部编译成功，
  18 个实际运行 rc=0；timings 因 OHOS busybox `ps` 不支持 `xjf` 选项、
  disk 因 OHOS 禁止读取 /proc/diskstats（Permission denied）无法完成展示，
  均非当前库适配缺陷，已在样例运行日志记录。

**examples/ 样例运行逐项结果**（cwd 均为 build/examples，
LD_LIBRARY_PATH=build/lib/.libs:<glib>/lib）：

| 样例 | 独立上游用例 | 运行 | 结果 |
|---|---|---|---|
| first | 否(样例) | 是 | rc=0（Method=1, 打印 CPU/内存信息）|
| second | 否(样例) | 是 | rc=0（打印 sysdeps features 列表）|
| pprint | 否(样例) | 是 | rc=0（进程列表打印）|
| procargs | 否(样例) | 是 | rc=0（打印自身 argv）|
| df | 否(样例) | 是 | rc=0（文件系统空间）|
| netlist | 否(样例) | 是 | rc=0（枚举 13 个网络设备）|
| mountlist | 否(样例) | 是 | rc=0（80KB 挂载点列表）|
| procmap | 否(样例) | 是 | rc=0（进程内存映射）|
| netload | 否(样例) | 是 | 无参数 rc=133（Usage 提示，需接口名）；`netload lo` rc=0 |
| sysdeps | 否(样例) | 是 | rc=0（sysdeps 能力位）|
| timings | 否(样例) | 部分 | rc=124：内部调用 `ps xjf`，OHOS busybox ps 不支持
| openfiles | 否(样例) | 是 | rc=0（进程打开文件）|
| smp | 否(样例) | 是 | rc=0（多核拓扑）|
| proclist | 否(样例) | 是 | rc=0（进程列表）|
| free | 否(样例) | 是 | rc=0（内存统计表格）|
| wd | 否(样例) | 是 | rc=0（工作目录）|
| affinity | 否(样例) | 是 | rc=0（CPU 亲和性）|
| disk | 否(样例) | 部分 | rc=134：/proc/diskstats Permission denied（OHOS 平台限制）|
| diskio | 否(样例) | 是 | rc=0（磁盘 IO 统计）|
| sysinfo | 否(样例) | 是 | rc=0（系统信息汇总）|

**全量通过率**：上游独立用例 0 个，0/0 不适用（无分母）；样例 19/19 编译、
18/19 实际运行通过、2 项平台限制（timings 需 GNU ps、disk 需 /proc/diskstats
读权限），已逐项记录命令/退出码/首错/恢复条件。

**test_package（消费者验证）**：1 个消费者用例（test_consumer.c），经 libgtop-2.0.pc
pkg-config 编译链接，公开 API 调用 glibtop_init/get_cpu/get_mem/get_uptime/
glibtop_close，运行输出
`libgtop consumer OK: cpu_total=38216023 mem_total=33464995840 mem_free=852238336 uptime=19581.8s`，
断言 4 项全部通过。
---

**编译结束**: 2026-09-09 22:32
**最终状态**: built
