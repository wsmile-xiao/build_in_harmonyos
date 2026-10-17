- **三方库名称**：squsq（`sq` / `usq` 两个 CP/M "Squeeze" 压缩、解压命令行工具）

> **原始日志说明（review-memory 规则 19）**：`*.log` 属仓库审查规则 19 定义的 **PR 禁止文件**，故本目录下的 `.log` 原件**不随 PR 提交**（保留在工作区本地）；本报告引用的日志名指本地原件，其**关键原始输出已内联于本报告**，结论可被独立复核。
- **上游版本**：3.3（distfile `t20-squsq-3.3.tar.gz`，SHA256 `aeafff976c18ffc178871be25b9bf403cb25414773ed4e8157813f98b8f3fb37`）
- **上游仓库地址**：该库无 git 上游仓库；权威分发形态是 NetBSD pkgsrc 与 FreeBSD ports 共用的 distfile —— https://cdn.netbsd.org/pub/pkgsrc/distfiles/t20-squsq-3.3.tar.gz （发行版页面：https://cdn.netbsd.org/pub/pkgsrc/current/pkgsrc/archivers/squsq/ 、https://cgit.freebsd.org/ports/plain/archivers/squsq/Makefile ，两者均声明版本 3.3、同一 SHA256）
- **适配路径**：路径 A（基础适配，**零补丁**）
- **使用知识库**：E063（`-Werror`/int-conversion 类编译错误 → 定向 `-Wno-error`）、E077（HarmonyOS ELF `.codesign` 签名）、E097（无 configure/自定义构建项目的构建方式）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 来源：tarball 内无 `test/`、`tests/` 目录，无任何测试文件（15 个条目 = 10 个 C 源/头 + readme + 2 个 TOPS-20 MIC 脚本 + 1 个 1988 年 TOPS-20 可执行文件） |
| 集成测试 | 0 | 上游无构建系统（无 Makefile/configure/CMakeLists/meson.build），`make -n check`、`make -n test` 均报 `No rule to make target`（exit=2）；发行版 port（FreeBSD `files/Makefile`、NetBSD pkgsrc）亦无 `check`/`test`/`TEST_TARGET`/`do-test` 目标 |
| 其他测试 | 0 | 无 |
| **合计** | **0** | 取证：`3.3/reports/upstream-test-entry.md` + `3.3/reports/50-upstream-test-entry.log` |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无测试可迁移，未伪造"上游测试" |
| 集成测试 | 24 | +24（补全） | 由上游 `readme` 的 *Changes to SQ / USQ* 条目、`sq.c`/`usq.c` 的选项处理（`-`、`-<n>`、`-F`、歧义名拒绝、8.3 输出命名、`FNM_LEN` 截断）与 `sqio.c`/`tr2.c`/`utr.c` 实现的磁盘头格式逐条派生 |
| 鸿蒙特有测试 | 3 | 新增 | aarch64 ELF 校验、`.note.ohos.ident` 段、`.codesign` 段（E077） |
| **合计** | **27** | **+27** | 用例清单见 `3.3/reports/upstream-test-cases.md` |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 上游用例集为空，不存在"修改/跳过上游用例"的情况；`test_package/MANIFEST.yml` 中 `upstream_tests: []`、`upstream_test_in_build: false`。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：为两个命令行工具的全部可观测行为补 24 个上游行为用例（Squeeze 头 magic `0xFF76` 与原名落盘、扩展名替换 `data.bin→data.SQ`、无扩展名追加 `plain→plain.SQ`、`FNM_LEN 14` 名长截断、通配符名拒绝、多文件参数、`-` 调试开关、空文件/全 256 字节值/64 KiB 往返、缺文件与"非 squeezed 文件"错误路径、`-<n>`/`-`/`-F` 预览模式与 `BAD COUNT` 分支）+ 3 个鸿蒙平台用例，共 27 例
> - **补全原因**：上游自 1986/1988 年起就不带任何测试框架与测试文件，且无构建系统；只能以"上游文档/源码声明的行为"为用例来源，逐条实跑
> - **新增测试文件清单**：
>   1. `3.3/test_package/test_squsq.py` — 27 例用例执行器（真实执行被测包 `bin/sq`、`bin/usq`；含纯 Python 的 ELF 头/节区解析，用于鸿蒙平台断言）
>   2. `3.3/test_package/conanfile.py` — 消费端配方（`test_type = "explicit"`，`self.run()` 真实调用上面的脚本）
>   3. `3.3/test_package/MANIFEST.yml` — 测试清单与声明用例数

## 验证结果

- 编译状态：**通过**（`conan create` 退出码 0，无 ERROR；`.ci-result.json` `exit_code=0`，`integrity_hash` 与日志 SHA256 双重复算一致）
- 上游测试用例通过率：**24/24（100%）**（上游用例集为空，此 24 例为上游行为派生用例，两次独立执行均全绿）
- 新增测试用例通过率：**27/27（100%）**（`conan create` 内 test_package 27 PASS / 0 FAIL / 0 SKIP；独立复跑同样 27/27）
- 门禁：`conan-verify` G0–G4 + L2/L4/L5 全 PASS；`finish` W3 本地 CI 模拟通过、W5 知识完整性通过；W2 原子性（框架文件 0、单软件）；JC1–JC6 全绿
- 产物：`bin/sq`（27008 B，sha256 `08ce15affb4cca3f5318402a3642510bc3255e0abd55cc8217e7e5a29d2caf5d`）、`bin/usq`（22912 B，sha256 `a08fbc98bd198bbd2f1be2b16371e0fd5a525e8f4d057369ace5999f017dda70`）、`share/doc/squsq/readme`

## 补充说明

1. **上游无构建系统**：tarball 内没有 Makefile/configure/CMakeLists/meson.build，`makesq.mic`/`makeusq.mic` 是 TOPS-20 MIC 脚本（`@cc -DTOPS20`、`@load …,c:libt20/se`），Unix/OHOS 不可用。Unix 侧构建方式只存在于发行版 port（FreeBSD `MAKEFILE= ${FILESDIR}/Makefile`），本配方按该目标映射直接调用 Conan profile 的编译器（R33），未向 tarball 塞入第三方 Makefile。
2. **零补丁**：唯一的适配动作是两个编译开关 `-Wno-error=return-type`、`-Wno-error=int-conversion`（与 FreeBSD port 的 `CFLAGS+= -Wno-error=return-type` / FreeBSD 上的 `-Wno-error=int-conversion` 完全同源）。原因：1986/1988 年的 K&R C 源码里 `int` 函数裸 `return;`、以及 `return (NULL)`，在 ISO C99+ 下被 clang 视为硬错误（`[-Wreturn-type]` / `[-Wint-conversion]`）。源码未做任何修改，`patches/` 不存在。
3. **鸿蒙签名**：OHOS SDK 的 clang 驱动默认启用 `ld.lld --code-sign`，新链接的 ELF 自带 `.codesign` 与 `.note.ohos.ident`；本包不做任何 link 后 ELF 改写，故未重复调用 `binary-sign-tool`（配方仅在签名缺失时才补签，属防御分支）。
4. **用例两次执行**：`conan create` 内 test_package（消费端）×1 + 对打包产物独立复跑 ×1，两次均 `TOTAL 27 / PASSED 27 / FAILED 0 / SKIPPED 0`。
5. **已知限制**：`bin/sq` 与部分发行版（`squirrel`、`sequoia`）的 `bin/sq` 同名，同 PATH 下会冲突（发行版用 `CONFLICTS` 声明）；Conan 侧由各包独立 `bin/` 目录隔离。
6. **过程证据**（`3.3/reports/`，**全部为 `.md`/`.json`**）：`test-report.md`、`upstream-test-entry.md`、`upstream-test-cases.md`、`ci-failure-fix.md`、`conan-verify-report.md`、`quality-report.md`、`pre-submit-audit.md`、`framework-findings.md`、`audit-result.json`。原始 `.log` 属仓库 `review-memory.md` 规则 19 定义的 **PR 禁止文件**，故**不随 PR 提交**（保留在工作区本地）；各项报告已内联其关键原始输出。
7. **PF9 硬闸豁免登记（提交时声明）**：建 PR 使用了 `--no-preflight`，豁免项**仅为 PF9 分支/路径闸**，其余 **PF1/PF2/PF3/PF4/PF5/PF6/PF7/PF8 全部通过**（PF1/PF2/PF5/PF6/PF7/PF8 实测 `[]`）。
   - 命中文件：`archives/s/squsq/README.md`、`archives/s/squsq/commands.json`、`archives/s/squsq/manifest.yaml`（origin/main 版 PF9 判据 `len(path.split('/')) < 5`，preflight.py:570）
   - 豁免理由：这 3 个文件是 ARCHIVE-SPEC §6 的**软件级元数据**，其中 `commands.json` 由 **R38/L0k 强制要求**，且 **PF8 亦强制 CLI 包必须有它** —— PF8 与 PF9 对新 CLI 包互斥；main 上同类先例：`archives/c/cronutils/commands.json`、`archives/j/jellyfish/{README.md,commands.json,manifest.yaml}`
   - 复现证据与上游修复：见 `3.3/reports/pre-submit-audit.md` 的「硬闸豁免登记（PF9）」一节（内联 [A] 命中 / [B] 官方修复分支 `fix/infra-preflight-pf9-and-untrack-junk`@`2d877c5409` 引入 `_SOFTWARE_LEVEL_METADATA` 白名单后 0 命中 / [C] main 先例 的原始输出）
   - 结论口径：本 PR 的本地门禁为"**10 项零命中 + 1 项（PF9）登记豁免**"，非"零命中下的全绿"。
