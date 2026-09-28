# hashids.c 1.2.2 适配笔记

## 编译环境
- 构建系统: autotools（`./bootstrap && ./configure && make`）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang）+ libtool 2.5.4（tool_requires）+ automake 1.18
- 状态: published（conan-verify 全部门禁通过后标记）

## 编译步骤
```bash
# 本地探索性编译（.work）：
PATH=/storage/Users/currentUser/tmp/libtool-2.5.4:$PATH ./bootstrap   # autoreconf 生成 configure
./configure --prefix=$DEFAULT_PREFIX && make -j1 && make check
# Conan 配方（conan-verify 干净构建）：
conan create archives/h/hashids.c/1.2.2 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=...ohos-aarch64 --build=missing
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | bootstrap 报 `Can't exec "libtoolize"` | 环境无 libtoolize（仅 autoconf 套件） | 本地注入 tmp/libtool-2.5.4；配方 tool_requires automake/1.18 + libtool/2.5.4 并 `autoreconf -fi`（同 abiword-plugin-clarisworks/argp-standalone） |
| 2 | configure `cannot guess build type` | config.guess 无法识别 HarmonyOS（uname -s=HarmonyOS） | 配方 generate() 显式 `--build/--host=aarch64-unknown-linux-ohos`（E540 同法） |
| 3 | HMDFS 下 config.status 临时目录不可写 | 生成 configure 含 `umask 077 && mktemp -d`，HMDFS setgid 后 0700 目录不可写（E114） | 配方 build() 中 drop umask 077 |
| 4 | make 报 jobserver fifo EPERM 警告 | HMDFS 不支持 jobserver fifo（E074） | build()/package() 均 `-j1` |
| 5 | test_package 加载失败 `SyntaxError: invalid syntax` | 模板类名 `Hashids.CTestConan` 含点号非法 | 改名 `HashidsCTestConan` |
| 6 | 首轮 conan-verify 时 inode 池耗尽 ENOSPC | 设备存储 inode 100% 占用（并发 worktree 物化风暴） | 运维释放 inode 后恢复；本轮 r03 正常 |

## 源码修改

无补丁（autotools 原生构建，未改任何上游源文件；配方内运行时调整 autoreconf/umask/triplet）。

## 依赖版本

- tool_requires: automake/1.18, libtool/2.5.4（构建期，registry 已有）
- 运行期依赖: 仅 libc（libm）

## 上游测试申报表（R51 完整枚举）

**口径**：官方 tag v1.2.2 源码 `hashids.c-1.2.2/` 全目录枚举。

| 入口 | 类型 | 分类理由 | 是否独立上游用例 | 实际运行 | 结果 |
|------|------|----------|------------------|----------|------|
| src/test.c | 用户测试源 | 唯一测试程序（`noinst_PROGRAMS=test`），main() 内 testcases[] 逐项断言 encode 输出 + decode 往返 | ✅（程序即用例集合，63 个 testcase 条目） | ✅ make check + 直接运行 | 通过（64 samples, 0 failures；63 真实条目 + 哨兵行计数） |
| Makefile.am TESTS=test | 构建目标/测试注册 | automake test harness 注册的独立可执行用例 | ✅ 1 个可执行用例 | ✅ make check | PASS=1 |
| src/hashids.c / src/hashids.h / src/main.c | 库/CLI 源码 | 被测对象，非测试 | ❌ | — | — |
| README.md 示例（encode ADf9h9i0sQ 等） | 文档样例 | 文档示例，非可执行测试 | ❌（不得误算） | — | 用于消费者测试断言 |
| .travis.yml | CI 配置 | 非测试 | ❌ | — | — |
| m4/ax_tls.m4 | autotools 宏 | 构建辅助，非测试 | ❌ | — | — |

**双口径统计**
- `source_declared_total` = **63**（src/test.c testcases[] 表条目数，按 `__LINE__` 标记逐条可复制枚举；程序 stdout "64 samples" 含哨兵行，实际断言条目 63）
- `configured_executable_total` = **1**（Makefile.am `noinst_PROGRAMS=test` + `TESTS=test` 在 OHOS 配置实际实例化的独立可执行用例）
- `executed_passed_total` = **1 个可执行用例运行，63/63 断言全部通过**（程序输出 `64 samples, 0 failures`，63 真实条目全过）
- 失败数 = 0；未运行/未实例化数 = 0
- 映射：src/test.c testcases[]（63 条目）→ noinst_PROGRAMS=test（编译目标）→ automake TESTS=test → `make check` 运行 ./test → 日志 `64 samples, 0 failures`（log: upstream-make-check-r03.log / upstream-test-run-r03.log）
- 全量通过率：**63/63（100.0%）**；当前配置可执行集合通过率 1/1（100%）

## 验证结果

```bash
$ make check            # rc=0, automake harness: # PASS: 1 # FAIL: 0
$ src/test              # rc=0, "64 samples, 0 failures"（63 断言条目 + 哨兵）
$ src/hashids 1         # => jR (CLI 编码)
$ src/hashids -d jR     # => 1 (CLI 解码)
$ conan-verify          # G0-G4 + L2/L4/L5 全 PASS（含 test_package 消费者测试）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | autotools 配方（bootstrap/umask/triplet/PATH/-j1） |
| conandata.yml | 官方 URL + SHA-256 91e55679… |
| test_package/ | 消费者测试（test.c 调公开 API）+ MANIFEST.yml（63 断言声明） |
| commands.json | R38 CLI 声明（bin/hashids） |
| manifest.yaml | 版本清单（published） |
| README.md | 软件级说明 |

## 注意事项

- hashids.c 为**库 + CLI** 双产物：`libhashids`（静态默认）+ `bin/hashids` 命令行工具（R38 需 commands.json）。
- 上游 tag 归档无 configure，必须 autoreconf；E114 umask、E074 -j1、E540 PATH 前置均已内建到配方。
- conan-verify E017 镜像注入会临时改写 conandata.yml 并在归档目录残留 `conandata.yml.ghfast-bak/.orig`，提交前需清理（W3 junk_check JC1 拦截）。

## 知识候选台账与查重（r03）

**判定：路径 A（reuse_existing / path_a_no_knowledge）— 全部候选被既有知识完整覆盖，无新增跨库可复用差异，不建草稿。**

| # | 候选（真实错误/根因/修复/验证） | 适用范围 | 正式知识查重 | 图谱查重 | 草稿查重 | 仓库先例查重 | 结论 |
|---|------|------|------|------|------|------|------|
| C1 | 上游 tag 归档无生成 configure：build() 需 `autoreconf -fi`，环境缺 automake/libtoolize → tool_requires automake/1.18 + libtool/2.5.4（实测 bootstrap rc=0） | 所有 GitHub tag 归档 autotools 库 | E058（configure missing/development snapshot）部分覆盖 | E041/E071/E089（autoreconf 相关） | 已有多个 autotools bootstrap 草稿 | abiword-plugin-clarisworks/argp-standalone 同法（已验证） | 部分覆盖，无新增差异 → 复用 |
| C2 | HMDFS setgid 使 `umask 077 && mktemp -d` 临时目录不可写：build() 中 drop umask 077（实测 configure rc=0） | 所有 HMDFS 上 autotools configure | E011（umask 077/config.status/mktemp，formal doc/E011.md）完整覆盖 | E114（can't create ./confXXXXXX/subs1.awk: Permission denied）完整覆盖 | E110/E112（HMDFS temp dir 相关） | 多个库已用 edit-umask-in-configure | 完整重复 → 复用（exact_duplicate） |
| C3 | config.guess 无法识别 HarmonyOS（cannot guess build type）：configure 显式 `--build/--host=aarch64-unknown-linux-ohos`（实测 configure rc=0） | 所有 autotools 库 on OHOS | E007（cannot guess build type，formal doc/E007.md）完整覆盖 | E007.kv/E072.kv（invalid triplet ohos）完整覆盖 | — | abiword/argp-standalone 同法（triplet 直传，已验证） | 完整重复 → 复用（exact_duplicate） |
| C4 | 工具路径缺失：make/autoreconf 经 PATH 解析失败 → 构建前置 /data/service/hnp/bin 等路径（E540 runner-path-prepend，实测 conan create rc=0） | 所有 OHOS conan/runner 构建 | E540（/data/service/hnp/bin PATH，draft）完整覆盖 | E540.kv | — | 多个库已用 runner-path-prepend | 完整重复 → 复用（exact_duplicate） |
| C5 | R38：产物含 bin/hashids CLI → 软件级 commands.json 必建 | 框架规则 | R38（SKILL 铁律） | — | — | 2048.c/aa3d 等 commands.json 先例 | 非知识候选（规则执行） |
| C6 | 上游测试枚举：63 testcase 断言条目 / TESTS=test 单可执行（实测 64 samples 0 failures，63 真实条目+哨兵） | 本库专属 | — | — | — | — | 非跨库知识（库专属台账） |

**七轴查重（路径 B 评估，结论均为不成立或未命中新增）**：
- exact_duplicate：C2/C3/C4 = true（E011/E114、E007/E072、E540 逐字覆盖）
- causal_duplicate：true（本库无独立新因果链）
- trigger_overlap：true（触发签名与既有条目完全重叠）
- solution_overlap：true（复用既有方案，无新解法）
- combination_novelty：false（autoreconf+triplet+umask+PATH 组合为既有条目组合，非新组合差异）
- boundary_novelty：false（无新边界/反例）
- test_migration_novelty：false（测试枚举为库专属，不跨库迁移）
- 关系字段：C1 similar_to E058（configure missing）；C2 caused_by E011/E114（HMDFS umask）；C3 caused_by E007/E072（config.guess 无 OHOS 分支）；C4 caused_by E540（runner PATH 缺 /data/service/hnp/bin）；与既有条目无 conflicts_with / prerequisite_of。
- **决定：reuse_existing（路径 A）**。理由：所有技术障碍均为既有知识条目（E007/E011/E114/E072/E540/E058）已覆盖的已知模式，本轮真实日志（bootstrap rc=0 / configure rc=0 / conan create rc=0 / 63/63 测试通过）验证了既有方案的有效性，但未产生可跨库复用的新增差异；按治理规则"完整重复且无独立差异时复用原条目"，不建 .md/.kv 草稿。
---

**编译结束**: 2026-09-27 02:46
**最终状态**: built
