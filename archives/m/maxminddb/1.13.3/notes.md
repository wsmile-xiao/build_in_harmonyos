# maxminddb 1.13.3 适配笔记

## 编译环境
- 构建系统: autotools（configure + make，兼有 CMakeLists.txt 双构建系统）
- 编译日期: 2026-09-07
- 编译器: clang/clang++（OHOS aarch64）
- 状态: built

## 编译步骤

```bash
# 1. 源码核验（官方 GitHub release 1.13.3）
#    SHA-256 a66502ea76eadbe17f2cd6fd708946777253972d2ae8157dee1b23a2fb528171
#    与 FreeBSD ports / Fossies 官方记录一致，SIZE=795830
# 2. config.guess/config.sub 打 OHOS 补丁（E007 既有知识）
perl scripts/patch-autotools-ohos.pl config.guess config.sub
# 3. configure（E052 修复：config.status mktemp 0700 目录在 HMDFS 不可写，
#    改用 $TMPDIR/conf$$ + mkdir -p，同 agetty 0002 模式）
export CC=clang CFLAGS="-fPIC -O2"
./configure --prefix=/storage/Users/currentUser/usr/local
# 4. 编译 + 安装（staging 隔离）
make -j1
make install DESTDIR=$TEST_PREFIX
# 5. 测试（make check，29/29 通过）
make check
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: cannot guess build type | GNU config.guess 无 HarmonyOS 分支 | patch-autotools-ohos.pl 打 config.guess/config.sub（E007） |
| 2 | config.status: can't create ./confXXX/subs1.awk: Permission denied | HMDFS 上 mktemp -d 0700 目录属主不可写（E052） | configure 中 mktemp 改 `$TMPDIR/conf$$` + `mkdir -p`（agetty 0002 同模式） |
| 3 | dump_t 测试 42/49 失败、dump 输出为空 | open_memstream 符号存在但 fclose 契约损坏（EBADF，buffer 不发布，Signal 5），E302 既有知识 | dump_t.c 改用 mkstemp + fdopen(w+) 命名临时文件，断言/预期数据不变（ldapvi E302 同模式） |
| 4 | compile_c++_t.pl/external_symbols_t.pl/mmdblookup_t.pl 被 skip | 系统 perl 缺 IPC::Run3/Test::Output 模块 | cpan 安装到 ~/perl5（PERL5LIB），恢复 3 个 Perl 测试真实执行 |

## 源码修改

- t/dump_t.c：open_memstream → mkstemp + fdopen("w+") 命名临时文件（E302，断言不变）
- configure：mktemp -d → $TMPDIR/conf$$ + mkdir -p（E052）
- config.guess / config.sub：OHOS 识别补丁（E007）

## 依赖版本

- 无外部 conan 依赖（纯 C 库，仅 libc/pthread/m）
- Perl 运行时模块（仅测试用，非库依赖）：IPC::Run3 0.049、Test::Output 1.036（装于 ~/perl5）

## 验证结果

### 上游测试全量枚举台账（t/ 目录，官方 tag 1.13.3 源码）

**双口径统计**：
- source_declared_total = **29**（t/Makefile.am `TESTS = check_PROGRAMS(26) + 3 Perl 脚本`）
- configured_executable_total = **29**（当前 OHOS autotools 配置全部实例化：26 个 C 测试程序构建成功 + 3 个 Perl 脚本注册执行）
- executed_passed_total = **29**，失败 = 0，未运行/未实例化 = 0
- 全量通过率 = **29/29 (100%)**（通过数/源码声明总数）
- 追加断言级口径：C 程序断言 2302 项全部通过 + Perl 断言 41 项全部通过 = 2343/2343

**枚举规则**：t/Makefile.am `check_PROGRAMS` 列出 26 个独立 C 测试程序（每个 `*_t.c` 一个独立 main 的 tap 用例），`TESTS` 另加 3 个独立 Perl 测试脚本。CMakeLists.txt `TEST_TARGET_NAMES` 注册同样的 26 个 C 程序（UNIX 分支补全 7 个），口径一致。

**逐项映射（源码声明 → 构建目标 → 注册 → 实际执行）**：

| 测试入口 | 类型 | 断言数 | 实际运行 | 结果 |
|---|---|---|---|---|
| bad_pointers_t | 用户测试源 C | 7 | 是（make check） | PASS |
| bad_databases_t | 用户测试源 C | 18 | 是 | PASS |
| bad_data_size_t | 用户测试源 C | 8 | 是 | PASS |
| bad_epoch_t | 用户测试源 C | 2 | 是 | PASS |
| bad_indent_t | 用户测试源 C | 7 | 是 | PASS |
| bad_search_tree_t | 用户测试源 C | 5 | 是 | PASS |
| basic_lookup_t | 用户测试源 C | 1437 | 是 | PASS |
| data_entry_list_t | 用户测试源 C | 65 | 是 | PASS |
| data-pool-t | 用户测试源 C（含 src/data-pool.c） | 76 | 是 | PASS |
| data_types_t | 用户测试源 C | 180 | 是 | PASS |
| double_close_t | 用户测试源 C | 10 | 是 | PASS |
| dump_t | 用户测试源 C（E302 修复后） | 49 | 是 | PASS |
| empty_container_metadata_t | 用户测试源 C | 6 | 是 | PASS |
| gai_error_t | 用户测试源 C | 4 | 是 | PASS |
| get_value_pointer_bug_t | 用户测试源 C | 14 | 是 | PASS |
| get_value_t | 用户测试源 C | 96 | 是 | PASS |
| ipv4_start_cache_t | 用户测试源 C | 12 | 是 | PASS |
| ipv6_lookup_in_ipv4_t | 用户测试源 C | 4 | 是 | PASS |
| max_depth_t | 用户测试源 C | 12 | 是 | PASS |
| metadata_pointers_t | 用户测试源 C | 6 | 是 | PASS |
| metadata_t | 用户测试源 C | 50 | 是 | PASS |
| no_map_get_value_t | 用户测试源 C | 7 | 是 | PASS |
| overflow_bounds_t | 用户测试源 C | 9 | 是 | PASS |
| read_node_t | 用户测试源 C | 106 | 是 | PASS |
| threads_t | 用户测试源 C（-pthread） | 110 | 是 | PASS |
| version_t | 用户测试源 C | 2 | 是 | PASS |
| compile_c++_t.pl | 用户测试脚本（C++ 编译/link 检查） | 6 | 是（装 IPC::Run3 后实跑） | PASS |
| external_symbols_t.pl | 用户测试脚本（符号导出检查） | 2 | 是 | PASS |
| mmdblookup_t.pl | 用户测试脚本（mmdblookup CLI） | 33 | 是 | PASS |

**非独立用例（框架/辅助/fixture，明确列出但未计入 29）**：
- `t/libtap/tap.c` / `tap.h`：libtap 测试框架实现（框架源码，非用户用例）
- `t/maxminddb_test_helper.c/.h`：测试辅助代码（open_ok/lookup_string_ok 等工具函数，非独立用例）
- `t/maxmind-db/`：Go 编写的测试数据库生成工具（fixture 生成器，非测试用例；Go 语言预检误判来源）
- `t/test-data/*.mmdb`（`t/maxmind-db/test-data/`）：MaxMind DB fixture 数据文件
- `t/CMakeLists.txt`：注册 26 个 C 测试目标（与 automake 一致的子集），无独立附加用例

**修复说明**：dump_t 为可运行但平台失败用例（E302 open_memstream 契约损坏），已按仓库既有模式（ldapvi）最小补丁修复并实测通过，非跳过/非伪造。3 个 Perl 测试原因缺 CPAN 模块被 skip，已安装 IPC::Run3/Test::Output 后恢复真实执行并通过（双口径统计按恢复后实跑计入）。

## 命令与证据
- make check：`All 29 tests passed`（exit 0）
- 日志：$TMPDIR/maxminddb-makecheck5.log；dump_t 修复验证：$TMPDIR/dump-verify2.log（49/49 ok）
---

**编译结束**: 2026-09-08 00:16
**最终状态**: built

## W3 基线隔离审计（baseline_isolation_audit）

W3 本地 CI 模拟首次失败命中其他库既有基线文件，按任务规则执行隔离复验：

| 字段 | 值 |
|---|---|
| path | archives/u/util-linux-login/2.42.2/.ci-trigger（util-linux-login 2.42.2 适配 PR 提交前已存在） |
| pre_sha256 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855（空文件） |
| isolation_command | `mv .ci-trigger $TMPDIR/.ci-trigger-baseline-backup` + `git rm --cached`（JC5 基于 git ls-files 扫描，需索引级隔离） |
| rerun_command | `python3 scripts/ohc-run.py finish maxminddb 1.13.3 built` |
| rerun_result | W3 本地 CI 模拟通过（build_and_test.sh RC=0，JC5 无命中） |
| restore_command | `cp 备份回原路径` + `git reset HEAD -- <path>`（还原索引跟踪） |
| post_sha256 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| pre==post | ✅ 一致 |
| 当前库 diff/staged/PR 含该路径 | ❌ 无（git status 该路径为空） |

结论：该文件为提交前已存在、允许范围外的其他库基线（空 .ci-trigger 标记），隔离复验通过后未修改、未提交、未入 PR，继续当前库审计与交付。

## 知识候选台账（knowledge_candidate_ledger）

### 候选清单与四范围查重

| # | 候选（真实错误/根因/修复） | 正式知识 doc/ | 图谱 graph/ | 草稿 drafts/ | 判定 |
|---|---|---|---|---|---|
| 1 | config.guess/config.sub 无 HarmonyOS 识别 → patch-autotools-ohos.pl（E007 方案） | E007 已覆盖 | E007 命中 | 无独立草稿 | exact_duplicate → 复用 E007，路径 A 组件 |
| 2 | config.status mktemp 0700 目录 HMDFS 不可写 → $TMPDIR/conf$$ + mkdir -p（E052 方案） | E052 已覆盖 | E052 命中 | 无独立草稿 | exact_duplicate → 复用 E052，路径 A 组件 |
| 3 | open_memstream fclose 契约损坏（EBADF/流不发布）→ mkstemp+fdopen 命名临时文件（E302 方案） | E302 已覆盖 | E302 命中 | 无独立草稿 | exact_duplicate → 复用 E302，路径 A 组件 |
| 4 | automake all-local `cd libtap` 在 out-of-tree 构建找不到子目录 → `cd $(top_srcdir)/t/libtap` | E434(copystamp) 签名不同；E522(libtool .la) 根因不同 | 未命中同签名 | 新建 E547-draft | trigger_overlap 但 signature/方案不同 → **new_draft E547** |
| 5 | lang-preflight 将测试夹具目录 vendored Go 工具（t/maxmind-db, 9 .go+go.mod）计为主体 → 误判 mixed(go)/env_unsupported | E543 仅覆盖 .rockspec 触发 | 未命中 Go fixture 触发 | 新建 E550-draft | trigger 同族(E543)但夹具目录 Go 触发为新增边界 → **new_draft E550** |

### 七轴查重（候选 4/5，对照 E434/E522/E543）

| 轴 | E547（out-of-tree all-local） | E550（lang-preflight Go fixture） |
|---|---|---|
| exact_duplicate | false（E434 签名 copystamp/cp same file，E522 签名 .la moved，均不覆盖 cd libtap 场景） | false（E543 触发物为 .rockspec，不覆盖 vendored Go 夹具） |
| causal_duplicate | false（根因=out-of-tree 目录结构，非 copystamp/libtool 迁移） | false（根因=源码统计未排除测试夹具目录，非 rockspec manifest 优先级） |
| trigger_overlap | true（同属 autotools/out-of-tree/VPATH 域，E434 vpath-build 方案同族） | true（同属 lang-preflight 对 C 库误判 mixed 族，E543 同族） |
| solution_overlap | partial（E434 vpath-build 是通用 VPATH 建议；`$(top_srcdir)` all-local 精确修复为新增） | partial（人工复核+--force 模式同 E543；夹具目录排除边界为新增） |
| combination_novelty | true（all-local cd + conan out-of-tree 组合未见于既有条目） | true（测试夹具目录 vendored 工具 + 语言统计组合未见于既有条目） |
| boundary_novelty | true（all-local/clean-local 相对 cd 的 out-of-tree 边界） | true（t/ 夹具目录不计入主体语言的边界） |
| test_migration_novelty | false（未涉及测试迁移） | false（未涉及测试迁移） |

### 路径判断

- 候选 1-3：完整重复 → `reuse_existing`（复用 E007/E052/E302 既有知识，路径 A 组件）
- 候选 4-5：已验证（本轮真实日志）、可跨库复用（E547：任意 autotools+out-of-tree；E550：任意 C 库附带 vendored 夹具工具）、查重为未命中/部分覆盖且有新增差异 → `new_draft`（E547/E550 草稿已建，.kv/.md 配对）→ **路径 B（知识库扩展）成立**，PR 前缀【知识库扩展】
- 结论：`new_draft`（2 项）+ `reuse_existing`（3 项）→ 路径 B，E547/E550 草稿随 maxminddb 归档同 PR 交付
