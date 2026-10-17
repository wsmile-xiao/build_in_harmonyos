# snapraid 14.9 适配笔记（OHOS aarch64）

## 任务信息
- 任务号: 10757 ｜ 分支: feat/snapraid-14.9 ｜ 基线: 8f56191952（upstream/main）
- 设备 worktree: ~/qzy/glm64-snapraid-14.9 ｜ CONAN_HOME: ~/tmp/ch/home-glm64-snapraid

## W0 依赖检查
- snapraid 为独立 autotools 工程，无外部库依赖（仅 pthread，随工具链提供）。
- conanfile.py `requirements()` 为空，W0/R36 通过。

## W0b 历史经验
- 归档树无 snapraid 历史（新适配）。上游为纯 C + autotools，CI 能力矩阵 ✅（gcc/clang/make ✅）。

## 语言预检（R47）
- lang-preflight 通过（milestone=lang_checked）。任务语言 cpp，源码主体 C —— c↔cpp 兼容族（R47），不迁移。

## 路径 B 判断
- **不走路径 B**。查重命中：HMDFS fallocate 平台限制已有知识（E115、E523、knowledge/drafts/DRAFT-libaudit-2.7.4-hmdfs-fallocate.kv、DRAFT-postgresql-fallocate-eacces-filezero.md）；autotools/HMDFS 适配已有 E007/E011/E114/E079 正式条目。本次全部为既有知识在单库的应用，无跨仓库复用的新知识增量。

## 上游测试三步法（R51）+ 五维账本（§10.1）
- `N_static` = **74**：Makefile.am `check-local` 配方中的测试块（80 个 `$(MSG)` 标记 − 3 个收尾非用例标记 − 3 个跨行描述行）。执行体 = `checker`（snapraid 全部源码 + checker.c 主函数变体）在 bench/ 六块模拟盘上按序执行 sync/check/scrub/fix/rehash/修复恢复等场景；`mktest` 负责生成测试数据。
- `N_registered` = **74**（`make check` 全部注册执行；另有上游 `fastcheck` 变体目标，不属于 make check 默认套件，不计入）。
- `N_executed` = **74/74**（真机实测 rc=0，耗时 5m01s，日志 ~/tmp/uc2/glm64-snapraid/makecheck.log）。
- 平台适配（逐项申报）：
  1. **套件级追加 `--test-skip-fallocate`**（经 CHECKFLAGS_COMMON 注入）：HMDFS 不支持 fallocate()，parity 预分配中止。该旗标为上游自带测试专用开关，上游已在套件多处自行使用（如 Makefile.am 的 sync -F 行）。影响：所有 sync/check 的预分配走缓冲写入路径。
  2. **patches/0001-Makefile.am.patch + patches/0002-Makefile.in.patch**：1 个子项 `--test-io-advise-direct` → `--test-io-advise-none`（Makefile.am:594 + Makefile.in:1589）：HMDFS 打开 O_DIRECT 返回 EINVAL，direct I/O 路径在本文件系统不可执行；该子项的 sync -F 断言仍以缓冲 IO 真实执行。
  3. **环境级（不改上游文件）**：`ln` PATH 垫片 —— "Create some more files, hardlinks..." 块的 4 条硬链接命令在 HMDFS（E079 不支持硬链接）自动回退 `cp -p`；符号链接透传真实 ln。该块正常执行，断言不变。
- `N_consumer` = **1**（test_package/test.sh）：以工具用户身份驱动真实安装的二进制，断言：sync 后 parity/content 文件非空、check rc=0、`-a check` rc=0、dup rc=0、list 输出包含两盘全部文件（grep）。全部通过。

## 编译环境
- 构建系统: autotools（tarball 自带 configure，无需 autoreconf）
- 编译日期: 2026-09-20
- 编译器: clang 15（OHOS aarch64，conan 2.29.1 OHOS 适配版）
- 状态: built

## 编译步骤
1. conan create（conanfile.py `build()`）：
   - `apply_conandata_patches`（patches/0001-0005：Makefile.am/Makefile.in 的 io-advise 适配；config.guess 的 HarmonyOS 分支；config.sub 的 ohos 三连；configure 的 umask 022）
   - `./configure --prefix=...`（原生探测，config.guess 输出 aarch64-unknown-linux-ohos）
   - `make -j2`（snapraid 主程序）
   - `make check`（上游 74 块套件；PATH 注入 ln 垫片 + CHECKFLAGS_COMMON 注入 --test-skip-fallocate）
2. test_package：VirtualRunEnv + bash test.sh（消费者测试）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure: cannot guess build type | config.guess 不识别 uname -s=HarmonyOS（E007） | patches/0003+0004：config.guess 增加 HarmonyOS→aarch64-unknown-linux-ohos 分支；config.sub 同步 ohos 三连与内核兼容表 |
| 2 | config.status: can't create confXXXX/subs1.awk: Permission denied | HMDFS umask 077+mktemp 目录 setgid 2700 不可写（E011/E114） | patches/0005：configure umask 077→022 |
| 3 | Failed to allocate all the required parity space | HMDFS 不支持 fallocate()，parity 预分配中止（E115 同类） | 套件级追加上游自带 --test-skip-fallocate 旗标 |
| 4 | ln: cannot create hard link ... Operation not permitted | HMDFS 不支持硬链接（E079） | 构建期生成 `ln` PATH 垫片：真实 ln 优先，EPERM 回退 cp -p；符号链接直接透传 |
| 5 | Error opening parity file ... Invalid argument | HMDFS 不支持 O_DIRECT（EINVAL） | patches/0001：该单一子项改用 --test-io-advise-none（缓冲 IO），断言不变 |
| 6 | configure: working directory cannot be determined（E386） | profile 的 CONFIG_SHELL 指向 hnp bash，在 HMDFS conan 缓存目录 getcwd 必挂 | E386 处方：从真实构建目录能力探测候选 shell（pwd 干净返回 0 才接受），以探测通过的 shell 路由 configure（env -u CONFIG_SHELL） |

## 源码修改
- patches/0001-Makefile.am.patch、0002-Makefile.in.patch：上游测试子项的 IO advise 平台适配（上文申报第 2 项，各 1 行）。
- patches/0003-config.guess.patch：HarmonyOS 识别分支（E007）。
- patches/0004-config.sub.patch：ohos 别名 case、OS 表项与 linux+ohos 内核兼容组合（E007）。
- patches/0005-configure.patch：`umask 077`→`022`（E011/E114）。
- snapraid C 源码零修改。

## 依赖版本
- 无外部依赖（pthread 随 OHOS musl 提供）

## 验证结果

```bash
# 上游套件（真机，CONAN_HOME=~/tmp/ch/home-glm64-snapraid）
make check   # rc=0，74/74 块通过，5m01s
# 消费者测试（conan create 内自动执行）
bash test_package/test.sh   # 全部断言通过（sync/check/-a check/dup/list）
```

## 注意事项
- commands.json 已声明（tool 型，R38）。
- `--test-skip-fallocate` 为测试期旗标：终端用户直接运行 snapraid（默认 io advise）行为不变；仅当文件系统不支持 fallocate 时 parity 预分配会显式报错，与上游在无 fallocate 平台上的行为一致。
---

**编译结束**: 2026-09-20 17:41
**最终状态**: built
