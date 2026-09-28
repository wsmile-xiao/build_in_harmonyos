# embedlog 0.7.2 适配笔记

## 编译环境
- 构建系统: autotools (autogen.sh/autoreconf bootstrap)
- 编译日期: 2026-09-25
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built (conan-verify G1-G4 PASS, W3 本地 CI PASS)

## 编译步骤
1. `init-build embedlog 0.7.2 --url=https://github.com/mlyszczek/embedlog/archive/refs/tags/v0.7.2.tar.gz`
2. tarball 不含生成 configure，需 `autoreconf -fi` 引导（配方 build() 内自动执行，tool_requires automake/1.18 + libtool/2.5.4）
3. `./configure --prefix=$DEFAULT_PREFIX --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos`
   （config.guess 无法识别 HarmonyOS 系统，显式三元组绕过，同 argp-standalone 先例）
4. `make -j1`（仅构建 include/src/tst；www 文档子目录需要 sphinx-build，从 SUBDIRS 移除）
5. `make check`（tst 分组测试，TAP 输出 30885 断言）
6. `conan create`（配 test_package 消费者验证）→ G2 PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 下载 404 | init-build 用 tag `0.7.2`，上游实际 tag 为 `v0.7.2` | 用 `archive/refs/tags/v0.7.2.tar.gz` |
| 2 | autogen.sh 缺 libtoolize | 环境未安装 libtool | 配方 `tool_requires("libtool/2.5.4")` |
| 3 | conan create configure 不可执行 | 源码拷贝丢失可执行位 (E490) | build() 内 chmod +x configure 等脚本 |
| 4 | config.guess 无法识别 HarmonyOS | GNU config.guess 无 HarmonyOS 分支 (E007) | configure_args 显式 `--build/--host=aarch64-unknown-linux-ohos` |
| 5 | make/install 在 www 子目录失败 | www 为 Sphinx 文档需要 sphinx-build | 补丁 0001-Makefile.am.patch 移除 www 子目录 |
| 6 | 测试 4 个 no_access 用例失败 | HMDFS chmod 不生效（权限固定 2775），EACCES 断言不成立 (E046) | 平台限制，记录不阻塞 |
| 7 | 测试 6 个 date_rotate 用例失败 | 依赖 libfaketime LD_PRELOAD 控制时钟；OHOS musl 无 GLIBC 版本符号无法构建 | 环境限制（已尝试源码构建 v0.9.13，ld.lld GLIBC 符号版本错误），记录不阻塞 |

## 源码修改
- patches/0001-Makefile.am.patch：SUBDIRS 移除 www（Sphinx 文档目录，非库交付物）

## 依赖版本
- automake/1.18（tool_requires，制品仓已有）
- libtool/2.5.4（tool_requires，制品仓已有）
- librb/2.0.0（上游测试依赖 ring buffer，制品仓已有，用于 make check 链接）

## 验证结果
- 上游 make check：TOTAL 30885 / PASS 30874 / FAIL 10（4 chmod 平台限制 + 6 faketime 环境限制）/ ERROR 1（wrapper exit 10 聚合）
- 源码声明（mt_run 注册）：173 个测试函数（options 27 + print 31 + file 77 + perror 3 + pmemory 19 + pbinary 16）
- conan-verify：G0-G4 PASS；test_package 消费者测试 PASS
- W3 本地 CI（build_and_test.sh，单包口径 JUNK_PR_DIFF）：PASS

## 交付物
- archives/e/embedlog/0.7.2/：conanfile.py + conandata.yml + test_package/ + patches/0001-Makefile.am.patch
- libembedlog.a（静态，R26 系统同名库隔离无冲突）
- 库类型（非 CLI），无 commands.json

## 注意事项
- embedlog 为 C 日志库，API：el_init/el_option/el_puts/el_print/el_flush/el_cleanup
- 上游测试依赖 librb（ring buffer）与 libfaketime（时间伪造），仅测试需要

## 知识候选台账（四范围查重 + 七轴查重）

### 候选 1：libfaketime（LD_PRELOAD 时间伪造）在 OHOS/musl 无法构建 → date_rotate 测试环境阻塞
- 真实错误：make check 6 个 `file_date_rotate_*` 断言失败（errno 9）；test_wrapper 用 `LD_PRELOAD=/usr/lib64/libfaketime.so`（不存在）；libfaketime v0.9.13 源码构建 ld.lld 报 GLIBC 符号版本错误（`pthread_cond_timedwait@@ has undefined version`、`timer_gettime@GLIBC_2.2 has undefined version`）
- 根因：OHOS libc 为 musl 系无 GLIBC 符号版本表，libfaketime 的 .symver 版本符号无法链接；FAKETIME env 无人消费
- 修复/处置：记录为环境限制（计入分母不计通过），提供恢复条件（等效 LD_PRELOAD 时间伪造库或上游时钟注入改造）
- 验证：`ls /usr/lib64/libfaketime.so` 无、`conan list faketime/* -r=ohpcd` 0 命中、libfaketime 源码 build 失败日志
- 适用范围：任何上游测试套件用 LD_PRELOAD=libfaketime + FAKETIME env 做时间敏感断言（日志轮转/时区/定时器）；反例：只依赖真实时钟或用 TZ= 时区的测试
- **四范围查重**：正式 graph（E001-E540）→ 未命中（faketime 全库 0 覆盖）；doc/ → 未命中；drafts/ → 未命中；index.tsv → 未命中
- **七轴**：exact_duplicate=no（无同题条目）；causal_duplicate=no（musl/glibc 兼容族 E020/E026 是根因族，非同题）；trigger_overlap=no（LD_PRELOAD faketime 触发无重叠）；solution_overlap=partial（E046 skip-test 处置思路类似，对象不同）；combination_novelty=yes（libfaketime+OHOS/musl+date_rotate 新组合）；boundary_novelty=yes（边界明确）；test_migration_novelty=yes
- 决定：**new_draft**（已建 `knowledge/drafts/DRAFT-embedlog-0.7.2-libfaketime-glibc-version-symbol-unavailable.kv/.md` 配对）→ 路径 B（知识库扩展）

### 候选 2：config.guess 无法识别 HarmonyOS（E007/E072 已覆盖）
- 本次采用显式 `--build/--host=aarch64-unknown-linux-ohos` 三元组（argp-standalone/abiword 先例），与 E007 的 patch-autotools-script 不同但等效；DRAFT-autotools-config-sub-silent-ohos-triplet 已澄清 Conan 同构 profile 下不注入三元组、config.sub 需成对补丁
- 七轴：trigger_overlap=yes、solution_overlap=yes → **reuse_existing**（E007/E072 + 既有草稿）

### 候选 3：release tarball 无预生成 configure 需 autoreconf 引导（E058/DRAFT-5982 已覆盖）
- 本次配方 build() 内 `autoreconf -fi` + tool_requires automake/1.18 + libtool/2.5.4
- 七轴：trigger_overlap=yes、solution_overlap=yes → **reuse_existing**

### 候选 4：HMDFS chmod 不生效致 4 个 no_access 测试失败（E046 已覆盖）
- 平台限制记录，不阻塞
- 七轴：trigger_overlap=yes、solution_overlap=yes → **reuse_existing**

### 候选 5（r02 新增）：config.status 用 mktemp -d 建 0700 临时目录，CI worker 上无法读写 subs1.awk → conan create 失败（DRAFT-6507-cln-mktemp-0700-hmdfs 同族）
- 真实错误：远端 CI #60560 `./config.status: line 820: ./confiCKLmd/subs1.awk: Permission denied` → `could not setup config files machinery`；本地同构 conan create 通过（本机 HMDFS 保留执行位），CI worker（uid 错位/setgid）下 mktemp 恒 0700 目录不可访问
- 根因：autoconf config.status 的 CONFIG_FILES 机制用 `tmp=`(umask 077 && mktemp -d "./confXXXXXX")` 建临时目录，mktemp -d 恒 0700 不随 umask；HMDFS setgid 父目录 + uid 错位语义（E011 家族）下写入 subs1.awk 被拒
- 修复/处置：配方 build() 在 autoreconf 后对生成的 configure 打补丁——跳过 mktemp，改用 `tmp=./conf$$-$RANDOM; (umask 000 && mkdir "$tmp")`（mkdir 0777，创建时定权限），与 cln 1.3.7 实证方案完全一致；本地 CI 同构 conan create rc=0、完整 build_and_test.sh rc=0
- 验证：conan create 日志（`.ci_logs/conan_build_embedlog_0.7.2-r02-fixcheck2.log` sha256 74e66071...）含 "patched configure: mktemp temp-dir -> mkdir 0777"；W3 全绿
- 适用范围：任何 autotools 包在 CI/远端 worker 的 HMDFS（setgid + uid 映射）上执行 conan create 时；反例：本机/常规 POSIX 文件系统上 mktemp 0700 可用
- **四范围查重**：正式 graph（E001-E540）→ 未命中（mktemp-0700 无正式条目）；doc/ → 未命中；drafts/ → **命中 DRAFT-6507-cln-mktemp-0700-hmdfs（cln 1.3.7 同族草稿，UNMATCHED 待提升）**；index.tsv → 未命中
- **七轴**：exact_duplicate=no（无同题正式条目）；causal_duplicate=no（E046 是 chmod 不生效、E490 是 configure 执行位丢失，根因族不同）；trigger_overlap=yes（mktemp -d 0700 + confXXXXXX 触发完全一致）；solution_overlap=yes（mkdir 0777 方案与 cln 一致）；combination_novelty=no（同族再现，无新组合）；boundary_novelty=no（边界已被 cln 草稿界定）；test_migration_novelty=no
- 决定：**reuse_existing**（复用 DRAFT-6507-cln-mktemp-0700-hmdfs 草稿，本轮为第二实证，强化待提升条目的普适性；不新建 embedlog 专属条目，避免拼凑）

### 最终路径决定
**path_b_new_draft = new_draft（候选 1）**：新增核实时验证、可跨库复用（任何依赖 libfaketime 的 autotools 测试套件）且查重未命中 → 与 embedlog 三方库归档同 PR 交付 DRAFT .kv/.md 配对；候选 2/3/4/5 reuse_existing（E007/E072、E058/DRAFT-5982、E046、DRAFT-6507-cln），无 path_a_no_knowledge 场景。r02 新增候选 5 不新建条目（DRAFT-6507 已覆盖，避免草稿拼凑），其修复已入配方 build() 注释与知识草稿依据。
- 状态: built

### 对话 #1（r02 返工）
- 分析端验收 r01 结论：远端 CI #60560 在 conan-build-test 步骤失败——config.status 以 mktemp -d 创建 0700 临时目录，CI worker 的 HMDFS/setgid uid 语义下无法读写 subs1.awk，报 `Permission denied` / `could not setup config files machinery`；另两项缺口为 PR 测试统计 0/0/0 与鸿蒙特有测试缺失。
- 本轮处理：① 配方 build() 于 autoreconf 后把 config.status 临时目录创建改为 `tmp=./conf$$-$RANDOM; (umask 000 && mkdir "$tmp")`（mkdir 0777，同 cln 草稿 DRAFT-6507 实证方案），本地 CI 同构 conan create 与完整 build_and_test.sh 均 PASS；② 新增 test_package/test_ohos.c 鸿蒙特有测试（文件输出+大小轮转+单调时钟时间戳+pthread 线程安全）实跑通过；③ 按赛事模板重写 PR #12564 测试统计（上游 173 / 适配后 174，鸿蒙特有 1）。
- 知识台账：候选5（config.status mktemp-0700）七轴查重命中 DRAFT-6507-cln → reuse_existing，不新建条目。
---

**编译结束**: 2026-09-26 17:17
**最终状态**: built
