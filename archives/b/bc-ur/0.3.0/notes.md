# bc-ur 0.3.0 适配笔记

## 编译环境
- 构建系统: autotools（发布 tarball 自带预生成 configure + 手写 Makefile.in，无 Makefile.am）
- 编译日期: 2026-09-25
- 平台: HarmonyOS PC (aarch64, musl libc + clang/clang++ 15 / libc++)
- 编译器: clang 15.0.4（/data/service/hnp/bin，OHOS SDK 工具链）
- 状态: built（本地 W3 全绿；合并 main 后由 CI release 流水线发布 CNB）
- 官方源: https://github.com/BlockchainCommons/bc-ur (tag 0.3.0)
- 依赖: 零第三方依赖（纯 C++17，内部自带 sha2/crc32/memzero/xoshiro256 实现）

## 编译步骤

```bash
# 源码包（GitHub 官方 archive 端点，SHA-256 已核验）
#   url: https://github.com/BlockchainCommons/bc-ur/archive/refs/tags/0.3.0.tar.gz
#   sha256: 2b9455766ce84ae9f7013c9a72d749034dddefb3f515145d585c732f17e7fa94
./configure --prefix=/storage/Users/currentUser/usr/local        # exit 0
make                                                             # exit 0（libbc-ur.a + 12 公开头）
make check                                                       # ./test → "*** ALL TESTS PASSED ***" exit 0
make install DESTDIR=.../test-install-bc-ur-0.3.0                # exit 0（staging 隔离验证）
python3 scripts/ohc-run.py conan-init bc-ur 0.3.0                # 生成配方
python3 scripts/ohc-run.py conan-verify bc-ur 0.3.0              # G1-G4 + L2/L4/L5 全过
```

Conan 配方要点：`package_type = "static-library"`（上游仅产出静态库，无 libtool/shared 目标）；
`layout()` 折叠 `self.folders.build = "."` 强制 in-source 构建（见知识候选 C1）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create G2: `Package type is 'library', but no 'shared' option declared` | conan 2.29.1 对 `library` 类型强制要求 `shared` option；bc-ur 上游仅产出静态库 | `package_type = "static-library"`（仓库内 adept-math 等同款先例） |
| 2 | conan create package(): `install: bad 'bc-ur.hpp': No such file or directory` | 手写 Makefile.in（无 Makefile.am）的 install 规则以裸名引用头文件（无 `$(srcdir)` 前缀），out-of-source 构建下 make 的 VPATH 不重写 recipe 变量 | `layout()` 中 `self.folders.build = "."` 强制 in-source 构建（知识候选 C1，草稿 DRAFT-bc-ur-0.3.0-makefile-install-bare-name-in-source） |
| 3 | `make: jobserver mkfifo ...: Operation not permitted`（HMDFS 不支持 mkfifo） | -j 并行 jobserver fifo 创建被拒 | 非致命（自动降级串行）；配方 `-j1` 规避；正式条目 E074 已覆盖，复用 |
| 4 | 上游 tag 0.3.0 的 configure.ac 仍声明 `AC_INIT([bc-ur], [0.2.0])` | 上游打 tag 时未同步 bump configure.ac（文档瑕疵，不影响构建/打包） | conanfile.py `version = "0.3.0"` 显式固定；`./configure --version` 报告 0.2.0 仅属观察记录 |
| 5 | `make check` 输出 `/bin/sh: tput: inaccessible or not found`（×2） | 上游测试框架用 tput 做彩色输出，OHOS 无 tput 命令 | 纯外观降级：用例照常全部通过（"ALL TESTS PASSED"），属噪声不构成知识候选 |
| 6 | 知识引擎在 G2 误命中 E540（runner PATH） | E540 签名含 make/autotools 关键字，本次失败根因实为 install 裸名（问题 2） | 以 conan create 实际日志为准定位，E540 不适用（本机 profile buildenv 已提供 PATH） |

## 源码修改

无（零补丁：OHOS aarch64 上无修改编译通过）。`patches/` 为空，`conandata.yml` 无补丁声明。

## 上游测试枚举台账（双口径）

源码 59 文件（src/ 库源码 28 个 C/C++ 文件 + test/ 测试 3 文件 + 配置/文档）。

| 入口 | 类型 | 是否独立上游用例 | 是否运行 | 结果 |
|---|---|---|---|---|
| test/test.cpp（21 个 `test_*` 用例函数，main() 逐序调用） | 用户测试源（assert + assert_throws 断言框架） | ✅ 21 个独立用例：crc32 / bytewords×2 / rng×3 / find_fragment_length / random_sampler / shuffle / partition_and_join / choose_degree / choose_fragments / xor / fountain_encoder / fountain_encoder_cbor / fountain_encoder_is_complete / fountain_decoder / fountain_cbor / single_part_ur / ur_encoder / multipart_ur | ✅（make check → ./test） | 21/21 全过（"*** ALL TESTS PASSED ***" exit 0） |
| test/test-utils.cpp / test-utils.hpp | 测试辅助（make_message/make_message_ur/assert_throws） | ❌ 非独立用例（被 test.cpp 引用） | ✅（编译进 test 二进制） | 不计数 |
| src/*.{cpp,c,hpp,h}（28 文件） | 库实现/公开头 | ❌ 非测试 | — | — |
| 样例/基准/fixture/脚本 | 无（tarball 无 example/benchmark/fixture 目录） | ❌ | — | — |
| 构建目标 | `test`（test/Makefile，链接 libbc-ur.a + test-utils.o） | ✅ 1 个可执行 | ✅ | exit 0 |

**双口径统计**：
- `source_declared_total = 21`（test.cpp 中 21 个独立 `test_*` 用例函数，main() 注册调用）
- `configured_executable_total = 1`（test/test 单一可执行；无 ctest/GTest 注册项）
- `executed_passed_total = 21`（./test 实际执行 21 个用例全部通过）
- 失败 = 0，未运行/未实例化 = 0
- **全量通过率 21/21 (100%)**；映射：test.cpp 用例函数 → test/Makefile 单一 `test` 目标 → make check 实际运行 → "ALL TESTS PASSED"
- 依赖可用性复查：本库零依赖，无因依赖跳过的测试入口（不适用）

## 消费者用例与鸿蒙专项测试（test_package，conan create 内实际运行）

| 测试 | 文件 | 内容 | 结果 |
|---|---|---|---|
| 消费者测试 | test_package/test.cpp | 仅经公开头 `<bc-ur/bc-ur.hpp>` 使用公开 API：Bytewords 已知向量精确编码/往返解码、单部分 UR 编解码往返、32767 字节多部分 fountain 分片收齐恢复 | "bc-ur consumer test: ALL PASSED" exit 0 |
| 鸿蒙专项测试 | test_package/ohos_test.cpp | `-Wall -Wextra -Werror` 严格编译：crc32 已知向量（"Hello, world!"=ebe6c6e6）、Bytewords minimal 往返、256 KiB 大消息 fountain 流式解码逐字节还原 | "bc-ur ohos test: ALL PASSED" exit 0 |

- 构建/运行命令（conan create 内）：`cmake --build test_package/build/...` → `./test_bc-ur`、`./test_bc-ur_ohos`（self.run env=conanrun）
- 调用的公开 API：`ur::Bytewords::encode/decode`、`ur::UREncoder/URDecoder`、`ur::CborLite::encodeBytes/decodeBytes`、`ur::crc32_bytes/string_to_bytes/data_to_hex`
- 与上游测试分别计数（上游 21 用例 + 消费者 + 鸿蒙专项，无重复充数）

## 知识候选台账（knowledge_candidate_ledger）

### C1. autotools 手写 Makefile.in（无 Makefile.am）out-of-source 下 install 裸名头文件失败 → 配方强制 in-source
- 真实错误/根因: `conan create` package() `make install` 报 `install: bad 'bc-ur.hpp': No such file or directory`（附完整命令、退出码、日志见 reports/conan-create.log）；根因 = 手写 Makefile.in 的 install 规则 `install $(HEADERS) $(includedir)` 以裸名引用头文件（无 `$(srcdir)` 前缀），GNU make VPATH 不重写 recipe 变量，out-of-source（basic_layout build-release/）下 install 找不到头文件；automake 生成的 Makefile 用 `$(srcdir)` 故不触发
- 修复: `layout()` 中 `self.folders.build = "."` 强制 in-source（仓库 abc/abduco/acpitool 同款做法）
- 验证: 修改后 conan create G1-G4/L2/L4/L5 全过（exit 0），test_package 2/2 通过
- 适用边界: 发布 tarball 无 Makefile.am 的 autotools 库；automake 生成式 Makefile 不适用；CMake 不适用
- 正式知识/图谱/草稿四范围查重:
  - index.tsv ↔ graph/*.kv: E041（automake 版本/VPATH 重生成）、E514（install-sh 源内根）、E074（jobserver FIFO）、E490（脚本执行位）——均不同签名
  - knowledge/doc/: 无命中
  - knowledge/graph/: 无同签名条目
  - knowledge/drafts/: DRAFT-audacious-buildsys-in-source-static-chain（同"手写构建系统→in-source"大类，但触发面不同：audacious 是 make 找不到 makefile，本条是 install 裸名失败）；DRAFT-kytea-0.4.7-stale-shipped-configh-breaks-vpath（VPATH 时间戳，不同）；DRAFT-ohos-makefile-explicit-toolchain-and-install-vars（不同）
- 七轴查重: exact_duplicate=否; causal_duplicate=部分（audacious 因果族）; trigger_overlap=部分（make phase vs packaging phase）; solution_overlap=高（folders.build='.'）; combination_novelty=是（VPATH 可编译但 install 裸名组合无条目）; boundary_novelty=是（automake $(srcdir) vs 手写裸名边界）; test_migration_novelty=是（conan-verify 全绿 + 2/2 实测可跨库复用）
- 关系: similar_to=DRAFT-audacious-buildsys-in-source-static-chain; caused_by=上游手写 Makefile.in install 规则未用 $(srcdir); prerequisite_of/conflicts_with=无
- 既有条目覆盖部分: audacious 草稿覆盖"无 VPATH → makefile not found → in-source"；未覆盖"VPATH 可编译但 install 裸名失败"的 packaging-phase 触发面
- 本轮新增部分: install-phase 裸名头文件签名 + automake/手写 $(srcdir) 差异边界 + bc-ur 实测验证证据
- 决定: **new_draft**（路径 B：候选已验证、可跨库复用、查重部分覆盖且存在新增差异）——已建 knowledge/drafts/DRAFT-bc-ur-0.3.0-makefile-install-bare-name-in-source.{kv,md} 同 stem 草稿对，随本归档同一 PR 交付

### C2. make jobserver mkfifo Operation not permitted（HMDFS 不支持 mkfifo）
- 真实错误: `make: jobserver mkfifo: /storage/Users/currentUser/tmp/GMfifo44560: Operation not permitted`（make install -j20 时出现，自动降级串行，非致命）
- 查重: **exact_duplicate=是**（正式条目 E074 已完整覆盖 make -j jobserver FIFO/Permission denied/SELinux 模式，含 env-var-override 方案）
- 决定: **reuse_existing**（引用 E074，不新建草稿；配方以 -j1 规避）

### C3. `tput: inaccessible or not found`（make check 彩色输出降级）
- 真实错误: 上游测试框架调用 tput 着色，OHOS 无 tput；用例照常全部通过
- 查重: exact_duplicate=否（知识库无 tput 条目）；但属纯外观噪声、无跨库可复用修复动作（除安装 ncurses-bin 外无修复点）
- 决定: **path_a_no_knowledge**（噪声，不构成知识候选，随本库台账申报）

### C4. 上游 tag 0.3.0 configure.ac AC_INIT 版本未同步（0.2.0）
- 真实情况: `AC_INIT([bc-ur], [0.2.0])` 在 0.3.0 tag 中未 bump；不影响构建与打包（conanfile version 显式 0.3.0）
- 查重: 无既有条目（各库版本瑕疵各自独立，无跨库可复用构建知识）
- 决定: **path_a_no_knowledge**（库内观察记录）

## 路径判定

**路径 B（知识库扩展）**：C1 为已验证、可跨库复用、查重部分覆盖且存在新增差异的知识候选 → 建立 DRAFT-bc-ur-0.3.0-makefile-install-bare-name-in-source.{kv,md} 草稿对，与 bc-ur 0.3.0 归档进入同一 PR；PR 前缀 【知识库扩展】。

## 平台限制备注（非阻塞）

- finish step3 G0 干净构建验证：在 `~/tmp/ohc-verify-bc-ur-*` 临时目录运行 configure 报
  `shell-init: getcwd: cannot access parent directories: Not supported` +
  `configure: error: working directory cannot be determined` —— 已知 HMDFS getcwd 限制
  （同类草稿: DRAFT-10251-libnfc-tools-configshell-bash-getcwd-hmdfs、DRAFT-6487-classads-configshell-hmdfs-getcwd）。
  该步骤非阻塞（SKILL Step 3 表）；真实干净构建 via `conan create`（G2）与 W3 本地 CI 模拟均通过，非配方问题，跳过并如实记录。
- finish step6/10 finalize 告警：软件级 README.md 已补建；release/debug tar.gz（packaging/）属 release 阶段产物，status=built 不要求。

## Conan 验证与 W3

- conan-verify（G1-G4/L2/L4/L5）全过：reports/conan-verify-report.md
- 消费者 + 鸿蒙专项 2/2 通过：reports/conan-create.log（test_package test() 实际执行）
- E490（autotools 脚本执行位）告警不适用：tarball 保留 configure/install-sh 执行位，conan get 正常执行
- 知识图谱 G2 命中 E540（runner PATH）为误命中：本次失败实为 C1（install 裸名），修复后全绿

---

## R02 返工（远端 CI L1 失败修复，task bc-ur-0.3.0-r02-pc2-34-20260925T064500Z）

### CI 失败与修复
- 远端 CI（PR 12565）L1 首错: `./config.status: line 604: ./conflMNNfB/subs1.awk: Permission denied` +
  `config.status: error: could not setup config files machinery` → `autotools.configure()` Error 1
  （CI 构建目录 /storage/Users/currentUser/.cache/conan2/p/b/... 位于 OH 设备 HMDFS 用户存储）。
- 根因: autotools configure 生成的 config.status（L604-694）在构建目录创建并读取临时 awk 脚本
  `$ac_tmp/subs1.awk`（ac_tmp=./conflMNNfB）；HMDFS 不保留/不允许 POSIX 权限位 → EACCES。
- 修复（按任务 worktree SKILL.md 平台约束规则）: 将 Conan cache（CONAN_HOME）与 TMPDIR/TMP/TEMP
  迁移到保留 POSIX 权限的合格文件系统（/data/storage/el2/base 为 tmpfs）:
  - `mkdir -p /data/storage/el2/base/oh-bc-ur-r02/{cache,tmp} && chmod 700 ...`
  - stat 实测: `/data/storage/el2/base/oh-bc-ur-r02 drwx------ 700`（cache/tmp 同为 700，tmpfs 保留真实权限位）
  - 干净重建: `conan create`（OHOS aarch64 profile）→ `configure: creating ./config.status; config.status: creating Makefile / src/Makefile / test/Makefile / config.h`（**无 Permission denied**），
    G1-G4/L2/L4/L5 全过，test_package 消费者 + 鸿蒙专项 ALL PASSED（日志 21-r02-conan-verify-qualified-fs.log、reports/conan-create.log）
  - W3 本地 CI 模拟通过（.ci-result.json exit_code=0）
- 附带现象处置:
  - predl 预下载因设备无 curl 二进制失败（框架自动回退 conan 下载成功）；conandata.yml 已还原官方 URL（提交前复核无污染）。
  - `configure: WARNING: unrecognized options: --disable-shared --enable-static`：来自 Conan
    AutotoolsToolchain 对 `package_type=static-library` 的默认注入（conan/tools/gnu/autotoolstoolchain.py
    L340-346），非本库配方瑕疵；仅警告非致命，configure 照常成功，处置为记录不修改。
- finish 复验备注: step3 G0 clean-verify 的 scratch configure 探针在 TMPDIR（tmpfs）下仍报
  `shell-init: getcwd: cannot access parent directories: Permission denied`——属框架 scratch
  探针自身的环境现象（非阻塞步骤，SKILL Step 3 表），与 CI 真实失败（config.status 临时 awk EACCES）
  无关；真实干净构建（conan create G2/W3）在合格文件系统上 config.status 全部正常生成。

### R02 知识候选台账（更新）

### C5. autotools config.status 临时 awk 脚本（subs1.awk）在 HMDFS 上 Permission denied → 迁移构建目录/使用 tmpfs
- 真实错误/根因: `config.status: line 604: ./conflMNNfB/subs1.awk: Permission denied` +
  `could not setup config files machinery`（HMDFS 不保留 POSIX 权限位 → EACCES）
- 修复: CONAN_HOME + TMPDIR 迁移到保留 POSIX 权限的 tmpfs 目录（stat 实测 drwx------ 700），干净重建通过
- 验证: conan create G1-G4/L2/L4/L5 全过，config.status 成功生成全部 Makefile（无 Permission denied）；
  本库 R02 实测为既有方案的新实例证据
- 四范围查重:
  - index.tsv ↔ graph/*.kv: **E011**（umask/edit-umask-in-configure）、**E052**（modify_tmpdir）、
    **E060**（use-tmpfs-workaround，error_signature 含 `subs1.awk.*Permission denied`）、**E110**
    （use_alternate_build_dir）、**E112/E114**（bypass-mktemp）、**E118**（patch-script）、
    **E125**（relocate-build-dir，error_signature 含 `can't create .* subs1.awk.*Permission denied`）——同签名同方案族
  - knowledge/doc/: E011/E052/E060/E110/E112/E114/E118/E125 文档齐全
  - knowledge/graph/: 同上（正式条目覆盖充分）
  - knowledge/drafts/: **DRAFT-6507-cln-mktemp-0700-hmdfs**（mktemp 0700 + HMDFS setgid 目录写权限，同族细分）
- 七轴: exact_duplicate=是（E125/E060 同 error_signature 同方案）; causal_duplicate=是（HMDFS 权限位）;
  trigger_overlap=高（config.status 临时 awk EACCES）; solution_overlap=高（E060 tmpfs / E125 relocate-build-dir 与本轮一致）;
  combination_novelty=否; boundary_novelty=否（边界=HMDFS 挂载下 autotools configure，E011 affected_scope 已明列）;
  test_migration_novelty=否
- 关系: similar_to=E011,E052,E060,E110,E112,E114,E118,E125,DRAFT-6507-cln-mktemp-0700-hmdfs;
  caused_by=HMDFS 不保留 POSIX 权限位; prerequisite_of/conflicts_with=无
- 既有条目覆盖部分: E060/E125 已给出"tmpfs/迁出 HMDFS 构建"完整方案；E011 给出 umask 层修复（本库未采用，配置脚本未硬编码 umask 077）
- 本轮新增部分: 无（本库实测是既有方案的执行实例，未发现新差异）
- 决定: **reuse_existing**（引用 E060/E125/E011 等；本库 R02 stat 0700 证据与干净重建结果随本库台账申报）

### R01 草稿对复核（DRAFT-bc-ur-0.3.0-makefile-install-bare-name-in-source.{kv,md}）
- 配对: .kv/.md 均存在且字段对齐（同 stem）；SHA-256: kv=5552dcf8c50cf145034ba6b5f8e1087f55d541389997d9549cc4edddba7e5275, md=51d9b5712b6fc135527128bd897ffc1c5ccba127b3d037cd5f514fecb529c688
- 适用边界复核: C1（手写 Makefile.in install 裸名 → in-source）与 R02 失败现象（config.status 临时 awk EACCES）
  正交——R02 CI 失败发生在 build() configure 阶段（install 之前），不否定 C1 修复；R01 草稿内容无需修正，
  本轮 R02 修复（合格文件系统迁移）按 C5 归并到既有条目族，不另立草稿。
- 结论: R01 草稿对保持有效（随 R01 已入 PR 12565）。

### R02 路径判定
- 知识路径维持 **路径 B（知识库扩展）**（R01 已随包交付草稿对）；R02 本轮无新增草稿
  （C5 判定 reuse_existing），仅按返工修复并复验交付。

---

## R03 返工（远端 CI 同首错闭环，task bc-ur-0.3.0-r03-pc2-34-20260925T143500Z）

### CI 同首错与库内修复
- 远端 CI（PR 12565，R02 commit 3fbfce7214 后 /rebuild）仍以同一首错 L1 失败：
  `config.status: line 604: ./conffHojbF/subs1.awk: Permission denied` +
  `could not setup config files machinery`（新随机前缀 conffHojbF；CI 构建工作区固定
  /storage/Users/currentUser/.cache/conan2/p/b/...，HMDFS 不保留 POSIX 权限位）。
  R02 仅改 notes.md（无构建相关变更），本机 tmpfs 迁移不影响 CI → 同 EACCES 复现。
- **库内配方修复（R03）**：conanfile.py build() 探测构建目录所在文件系统是否保留
  POSIX 0700/exec 语义（mkdir 0700 + stat 实测 + exec 探测；HMDFS 归一化 2771/760
  → 判不合格），不合格时复制源码到保留权限的合格挂载点（/data/storage/el2/base
  等 tmpfs，stat 实测 drwx------ 700）执行与 Autotools helper 一致的
  configure（args 读 conanbuild.conf）/make -j1/make install DESTDIR=package_folder，
  再打包；无合格挂载点回退原位并记录恢复条件。package() 仅清理专用构建根
  （守卫 basename 前缀），不触碰挂载根本身。
- **复验（CI 等价路径）**：CONAN_HOME=/storage/Users/currentUser/.cache/conan2
  （HMDFS 构建工作区，CI 等价）下 conan-verify G1-G4/L2/L4/L5 全过；构建迁移到
  /data/storage/el2/base/.bc-ur-build-<pid>/src 后 config.status 成功生成全部
  Makefile（无 Permission denied）；test_package 消费者 + 鸿蒙专项 ALL PASSED；
  上游 make check 复跑 21/21；staging install exit 0；W3 本地 CI 模拟通过
  （.ci-result.json exit_code=0）；finish 完成（step3 G0 scratch 探针 getcwd 现象
  为非阻塞环境现象，step8 知识缺口为全局草稿计数信息）。

### 取证要点（R03 forensics）
- 本机 HMDFS（.cache/conan2 与 .conan2）上 `umask 077 && mktemp -d ./confXXXXXX`
  创建的目录被归一化为 2771（非 0700）、脚本 700→760，且写/exec 均成功 → 本机
  HMDFS 语义宽松，与 CI 严格设备（0700 目录内写入 EACCES）为 per-device 差异；
  tmpfs 严格保留 0700/700（stat 实测 + exec 探测通过）。
- 本机 W3 harness（zsh）heredoc 临时文件默认用 TMPPREFIX（/tmp/zsh，落在只读 /tmp）
  → 需 export TMPPREFIX=/可写目录（如 /data/storage/el2/base/oh-bc-ur-r02/tmp/zsh）
  才能通过 build_and_test.sh 的 L0i/L0m heredoc 门禁——本机运行环境观察（bash 复刻
  L0i 正常，非库交付知识），随本库台账申报（path_a_no_knowledge）。

### R03 知识候选台账（更新）

### C6. autotools 配方级自动修复：构建目录文件系统不保留 POSIX 0700/exec 语义（HMDFS）→ build() 探测合格挂载点并迁移构建
- 真实错误/根因: `config.status: ./conffHojbF/subs1.awk: Permission denied` +
  `could not setup config files machinery`（R01/R02/R03 三次同首错）；根因 = config.status
  以 `(umask 077 && mktemp -d ./confXXXXXX)` 创建 0700 临时目录写入 subs1.awk，HMDFS
  不保留 POSIX 权限位（归一化 2771/760 或 EACCES）；既有方案 E060/E125 为 runner/手动
  手段，CI 的 CONAN_HOME/工作区由框架固定，执行端无法落地 runner 手段
- 修复: conanfile.py build() 配方级自动探测（mkdir 0700 + stat + exec）+ 迁移构建到
  合格挂载点（tmpfs）+ 回退兜底；package() 仅清理专用构建根
- 验证: CI 等价路径（CONAN_HOME=.cache/conan2）下 conan-verify 全绿 + config.status
  无 Permission denied + 消费者/鸿蒙专项 2/2 + W3 通过（详见上文 R03 复验）
- 适用边界: 构建工作区固定在 HMDFS 且设备有可写 tmpfs 的 autotools 库；保留权限位的
  常规环境探测返回 False 原位构建；无合格挂载点回退原位
- 四范围查重: index/graph: E011/E052/E060/E110/E112/E114/E118/E125/E273（均为 runner/
  配置补丁手动手段，无配方级条目）；doc: 同上文档；drafts: DRAFT-6507-cln-mktemp-0700-hmdfs
  （configure 层 mkdir -m 0777，不同层）；operations: 无
- 七轴: exact_duplicate=否; causal_duplicate=部分（E060/E125 根因家族）;
  trigger_overlap=高（subs1.awk EACCES 同签名）; solution_overlap=部分（runner 手动 vs
  配方自动）; combination_novelty=是（配方自包含探测+迁移+兜底组合）; boundary_novelty=是
  （探测 mkdtemp 0700 语义边界）; test_migration_novelty=是（CI 等价路径复验全绿）
- 关系: similar_to=E060,E125,E011,E052,E110,E112,E114,E118,DRAFT-6507-cln-mktemp-0700-hmdfs;
  caused_by=HMDFS 不保留 POSIX 权限位; prerequisite_of/conflicts_with=无
- 既有条目覆盖部分: E060/E125 覆盖手动 tmpfs/迁出手段；E011 覆盖 configure umask 层
- 本轮新增部分: 配方级自动探测（stat 0700 语义 + exec 探测）+ 迁移 + 回退兜底机制，
  随库自包含交付，不依赖 runner 配合
- 决定: **new_draft**（路径 B）——已建 knowledge/drafts/DRAFT-bc-ur-0.3.0-autotools-recipe-relocate-build-qualified-mount.{kv,md} 同 stem 草稿对，随本归档同一 PR 交付

### C7. 本机 W3 harness zsh heredoc 临时文件（TMPPREFIX 默认 /tmp/zsh 落在只读 /tmp）
- 真实现象: 本机 `zsh ci/conan/build_and_test.sh` 的 L0i/L0m heredoc 报
  `can't create temp file for here document: no such file or directory`；bash 复刻 L0i
  正常；export TMPPREFIX=/可写目录 后 W3 全过（bash 用 TMPDIR，zsh 用 TMPPREFIX）
- 查重: 无既有条目（属本机工具链/运行环境观察，非库构建知识）
- 决定: **path_a_no_knowledge**（随本库台账申报；本机后续任务跑 finish/W3 需设
  TMPPREFIX，记录为恢复条件）

### R01/R02 知识复核
- R01 草稿对（DRAFT-bc-ur-0.3.0-makefile-install-bare-name-in-source.{kv,md}）配对存在、
  字段对齐；SHA-256 kv=5552dcf8c50cf145034ba6b5f8e1087f55d541389997d9549cc4edddba7e5275,
  md=51d9b5712b6fc135527128bd897ffc1c5ccba127b3d037cd5f514fecb529c688；适用边界仍成立
  （install 裸名 → in-source 与 R03 的 config.status EACCES 正交），无需修正
- R02 C5（config.status EACCES → 合格文件系统迁移）reuse_existing 结论复核成立；
  R03 的配方级自动迁移为 C5 家族的新机制增量，按 C6 建草稿，不改变 C5 结论

### R03 路径判定
- 知识路径维持 **路径 B（知识库扩展）**：R03 新增草稿对
  DRAFT-bc-ur-0.3.0-autotools-recipe-relocate-build-qualified-mount.{kv,md}（C6，
  配方级自动迁移机制，已验证可跨库复用），与 R01 草稿对同随 PR 12565 交付。
---

**编译结束**: 2026-09-25 16:42
**最终状态**: built
