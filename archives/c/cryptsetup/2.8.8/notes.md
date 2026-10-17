# cryptsetup 2.8.8 — OHOS (HarmonyOS PC) 适配笔记

- 上游: https://gitlab.com/cryptsetup/cryptsetup
- 源码: https://cdn.kernel.org/pub/linux/utils/cryptsetup/v2.8/cryptsetup-2.8.8.tar.xz
  (sha256 `3acfa685f2dd7fcc832e0b77bc7093aa7da554a51ce8dafbb4138eaa854eee35`，与官方
  `sha256sums.asc` 逐字比对一致)
- 构建系统: autotools（发行归档含预生成 configure/Makefile.in）
- 适配产出: libcryptsetup.so + cryptsetup/veritysetup/integritysetup CLI（sbin/ 归并入 bin/）

## 1. 依赖（R36 全部 conan download EXIT=0，空缓存探针）

| 依赖 | 用途 | pkg-config 名 |
| --- | --- | --- |
| lvm2/2.03.42 | libdevmapper（强制，configure.ac:92/:456） | devmapper（≠包名） |
| util-linux/2.42 | libuuid（强制）+ libblkid（:586，`--enable-blkid` 保功能） | 一包双供给 |
| json-c/0.18 | LUKS2 JSON 元数据（强制，:484） | json-c |
| popt/1.16 | CLI 参数解析（仅 src/*.c，:180） | popt |
| openssl/3.5.6.1.2 | crypto backend（:331，无 fallback） | 包级 openssl.pc 不可用 → 覆盖 |

可关闭项（均显式 disable）：asciidoc(:65 缺 asciidoctor 必 ERROR)、ssh-token(:492 缺
argp.h)、udev(:451)、selinux(:447)、nls。config.sub 2024 版原生支持 `ohos*`，无需 patch。

## 2. 平台适配点（全部有实证）

| # | 问题 | 根因 | 修法 |
| --- | --- | --- | --- |
| 1 | configure 临时目录失败 | E011: `(umask 077 && mktemp -d ./confXXXXXX)` 在 HMDFS 上生成 0700 目录后不可写 | 补丁 0001: `umask 077`→`umask 022`（mktemp 与 mkdir fallback 两条分支各一处；临时目录权限位由 0700 变为 0755） |
| 2 | `bad interpreter` Error 126 | E165: OHOS 无 /bin/bash | 补丁 0002: 119 个 `#!/bin/bash` → `/data/service/hnp/bin/bash` |
| 3 | 鸿蒙消费者用例 | 上游 34 项测试（31 字面 + verity/integrity/systemd-plugin 三个条件项）无一可脱离 dm-crypt 完整验证产物 | 补丁 0003: 新增 `tests/ohos-consumer-test` 注册进 TESTS（详见 §4） |
| 4 | `You need the uuid library.` | AutotoolsToolchain 不注依赖路径 | 自建 deps-view + CPPFLAGS/LDFLAGS（先例 216 配方） |
| 5 | `libtool: cannot find '//lib/libblkid.la'` | **util-linux/popt 纯静态包 .la `libdir='//lib'` 毒化 libtool**（AutotoolsDeps 注入真实 -L 是入口） | 弃 AutotoolsDeps → deps-view 实体复制 .a/.so（排除 .la）+ overlay pc 指向视图；fPIC 核验：util-linux fPIC=True(:37)，popt 仅 CLI 消费 |
| 6 | `cannot run C compiled programs`(rc77) | conftest 链共享依赖即运行，而 OHOS musl 不解析「SONAME 名是软链」的库（E505/E316），包目录注入也 127 | generate() 建 runtime-libs 实体视图 + LD_LIBRARY_PATH（探针实测：软链 127→实体 0） |
| 7 | `You need openssl library.` | PkgConfigDeps 只产包级 .pc（openssl 无 components）；configure.ac:331 按**库名**探 libcrypto 无 fallback | `_overlay_pc()` 自建 libcrypto.pc / blkid.pc 库级覆盖 |
| 8 | test_package CTest `Error loading shared library libjson-c.so.5` | CTest 不走 conanrun.sh；依赖 .so 是软链 | test_package 自建 ohos-runtime-libs 实体视图 + test() 注入 LD_LIBRARY_PATH |
| 9 | 断言错位两处 | ① 无 keyslot 时 `crypt_get_volume_key_size()==0` 是上游语义（segment→digest→keyslots 链）；② luksDump 实际输出 `Data segments:`/`Keyslots:` | test_cryptsetup.c：format 后 `crypt_keyslot_add_by_volume_key`（镜像 CLI 流）再断言 ==32；断言关键字改 Keyslots |
| 10 | make `-j` 并行 | R9/E074: HMDFS jobserver fifo EPERM | `autotools.make(args=["-j1"])` |
| 11 | detached header 创建必败（上游测试 compat-args-test / 消费者用例 luksHeaderBackup 路径） | HMDFS(FUSE) 不支持 `posix_fallocate`，返回 EOPNOTSUPP | 补丁 0004: 4 处 `posix_fallocate` 失败退化为 `ftruncate`（`src/cryptsetup.c`、`src/utils_reencrypt_luks1.c`、`src/utils_reencrypt.c`、`lib/utils_device.c`） |

**补丁 0004 的覆盖范围（含"为什么只改 4 处"的判据）**：上游 `src/`+`lib/` 共 6 个
`posix_fallocate` 调用点，本补丁覆盖其中 **4 个"失败即致命"**的站点；未覆盖的 2 处经查
**上游自身设计即为可忽略**，不属遗漏：

| 站点 | 上游行为 | 是否需改 |
|---|---|---|
| `src/cryptsetup.c:1528` | `fd == -1 \|\| posix_fallocate(...)` → 直接报错退出 | ✅ 已改 |
| `src/utils_reencrypt_luks1.c:188` | 同上，直接报错 | ✅ 已改 |
| `src/utils_reencrypt.c:735` | `r = posix_fallocate(...)` 失败后走错误路径 | ✅ 已改 |
| `lib/utils_device.c:679` | 失败后 `LUKS_check_device_size` 误报 "Device too small" | ✅ 已改 |
| `lib/luks2/luks2_luks1_convert.c:464` | 上游原文注释：`/* This can safely fail (for block devices). It only allocates space if it is possible. */`，失败仅 `log_dbg(...)` | ❌ 上游已容错，改它反而是无谓偏离上游 |
| `src/utils_reencrypt_luks1.c:656` | `if (posix_fallocate(...)) {};` 空体，返回值被显式丢弃 | ❌ 同上 |

（另 `lib/utils_device.c:709` 是注释行，非调用点。）


## 3. 构建迭代台账（收敛过程 1-11 轮 + 第 12 轮官方形态复建；每轮首错与修复均入表）

| 轮 | 结果 | 首错 | 修复 |
| --- | --- | --- | --- |
| 1 | 失败 | `You need the uuid library.` | +AutotoolsDeps（后由 #4/#5 演进为 deps-view） |
| 2 | 失败 | `cannot run C compiled programs` rc77 | runtime-libs 实体视图（#6） |
| 3 | 失败 | `You need openssl library.` | overlay pc（#7） |
| 4 | 失败 | `tests/generate-symbols-list: bad interpreter` | 补丁 0002（#2） |
| 5(worktree 1) | 失败 | `libtool: cannot find '//lib/libblkid.la'` | deps-view 弃 .la（#5） |
| 5(worktree 2) | 失败 | test_package libjson-c.so.5 加载失败 | test_package 实体视图（#8） |
| 6 | **成功** | — | Package created + test_package 层A 16/16 + 层B OHOS CLI 全过 |
| 7-10 | 迭代 | 补丁 0003（鸿蒙消费者用例）/ 0004（fallocate 回退）生成与重生成后的复建轮次 | 每次补丁重生成即复建验证，逐步收敛至 0004 定型 |
| 11 | **成功（终局）** | — | EXIT=0，package_id `1b792455…`；上游测试 35 项 make 口径全 rc=0（见 §5） |
| 12(官方形态复建) | **成功** | 环境（本机 shell 未 unset `CODEBUDDY_SAFE_DELETE_BIN_DIR` → `generate()` 走 `env.remove("PATH",…)` 分支抛 `KeyError: 'PATH'`） | 补 unset 后 EXIT=0；见 §6 镜像形态/官方形态 revision 对齐 |

日志（两处，均为真实构建证据）:
- `reports/conan-create-official.log`（第 12 轮，官方形态单配方复建，`--build="cryptsetup/*"`）：
  `Forced build from source` → 主包 `Calling build()` → `Package '1b792455…' built` → test_package 段。
- `reports/conan-create.log`（**2026-09-20 23:27 重跑 conan-verify 后的 G2 真编日志**：
  先 `conan remove cryptsetup/2.8.8@ohpcd/stable -c` 再 `python3 scripts/ohc-run.py conan-verify
  cryptsetup 2.8.8`，VERIFY_RC=0）：`Building from source`(:109) → `Calling build()`(:123) →
  `Package '1b792455…' built`(:475) → `Created package revision a6342cc25c…`(:552) →
  test_package `Passed 0.54 sec`(:641) / `100% tests passed`(:643)；源归档取的是
  `Source https://cdn.kernel.org/.../cryptsetup-2.8.8.tar.xz`(:105)。
  ⚠️ 该文件**此前**确为"G2 命中缓存"形态（只有 `Already installed!`、主包无 `Calling build()`），
  已通过 `conan remove` + 重跑修掉；G2 的构建触发词是 `Building from source`（`--build=missing`
  口径），与官方形态那份的 `Forced build from source`（`--build=<pkg>` 口径）语义等价。
  注意：**不可再重跑一次 `finish`**——其 Step 4 内嵌的 G2 会因包已在缓存而重新写成"命中缓存"日志，
  反而回退本项证据（详见 §7 #2）。

## 4. 新增鸿蒙测试用例（消费者可行性，补丁 0003）

`tests/ohos-consumer-test`（注册进 Makefile.am/Makefile.in 的 TESTS，成为 make check
基础项之一；**10 项断言**，全程不需要 root / dm-crypt / loop 设备）：

1. `--version` 横幅（CLI + libcryptsetup 自举）
2. `isLuks` 拒绝普通文件（负向）
3. `luksFormat --type luks2`（普通文件 + PBKDF2 快速参数）——真实构建 LUKS2 容器
4. `isLuks` 接受 LUKS2 容器（正向）
5. `luksDump` 元数据（命令成功）
6. `luksDump` 输出断言：LUKS2 `Keyslots` + `aes`（LUKS2 JSON 走 libjson-c）
7. `luksUUID`（libuuid 路径，36 字符格式）
8. `luksHeaderBackup`
9. `luksHeaderRestore`（与 8 构成闭环）
10. `open`（平台边界：无 dm-crypt 时必须非 0 干净失败；有 dm 则激活后即关，两态均算过）

（脚本末尾打印 `PASS: ohos-consumer-test (10 checks)`；失败时打印 `FAIL: … (n of m checks failed)` 并 `exit 1`
——该行是**汇总输出**，不计入上面 10 条断言。逐条原文见 `reports/test-report.md` 的断言表与
`upstream-testlogs/ohos-consumer-test.raw.log`。）

toybox patch 不落地 new file mode 的 exec 位 → 配方 build() 内 `chmod 0o755` 兜底。

## 5. 上游测试实跑统计（终局，官方形态构建树）

- 用例全集: 构建树 `tests/Makefile` 的 **TESTS = 35 项** = 字面 32（上游 31 + 本适配新增
  `ohos-consumer-test`）+ `am__append_1` verity-compat-test + `am__append_2` integrity-compat-test
  + `am__append_4` **systemd-test-plugin**（`config.h:#define USE_EXTERNAL_TOKENS 1` ⇒ 条件为真）；
  `am__append_3` ssh-test-plugin 因 `--disable-ssh-token` 未注册。
- 命令: 逐项 `make -C tests check -j1 TESTS=<name>`（35 项），构建树
  `p/b/crypt3a96fa5df70ca/b/build-release`（官方形态 revision `2eb8f920…`，conan create 第 12 轮）
- 结果: **make check 口径 35 项 rc=0 / 0 FAIL / 0 ERROR**。automake 逐项判定：**11 项真实执行 PASS**
  （bitlk-compat / blockwise-compat / compat-args / fvault2-compat / luks1-compat /
  ohos-consumer / run-all-symbols / tcrypt-compat / unit-utils-crypt-test / unit-wipe / vectors-test）
  + **24 项 SKIP**（21 项上游 root 门 `[ $(id -u) != 0 ] && exit 77`；
  2 项缺 jq：luks2-validation-test / luks2-reencryption-mangle-test；
  1 项上游 opt-in 门：systemd-test-plugin 的 `RUN_SYSTEMD_PLUGIN_TEST` 未定义）
- 新增鸿蒙用例 ohos-consumer-test: **10 断言全过**（6s，日志 `PASS: ohos-consumer-test (10 checks)`）
- test_package: 层 A C API **16 断言**全过，断言数三轮恒为 16、仅耗时随负载波动：
  `Passed 1.27 sec`（官方形态轮，`reports/conan-create-official.log:621`）/
  `Passed 0.55 sec`（W3 轮，`reports/w3-local-ci.log:791`）/
  `Passed 0.54 sec`（G2 真编轮，`reports/conan-create.log:641`，运行期证据
  `reports/test-package-lasttest.log`：`16 check(s) run, 0 FAILED`）；
  层 B OHOS CLI 用例全过（不含 restore，restore 由 ohos-consumer-test 第 9 条断言覆盖）
- 逐项名称/耗时/日志: `reports/test-report.md` 与 `.workbuddy/tmp/cryptsetup-2.8.8/upstream-testlogs/`
  （历史留档：`upstream-testlogs-round11-34items/` 第 11 轮 34 项清单、`upstream-testlogs-rerun/` 2 项复跑）
- 环境归因: 非 root、无 /dev/mapper、无 dm-crypt、无 jq——dm 激活类与 JSON mangle 类用例
  按上游脚本自身门控 skip；期间修复两个环境断裂（id shim 恢复 toybox 大 uid 断裂的 root 门；
  补丁 0004 修复 HMDFS fallocate 缺失导致的 detached header 创建必败——后者属真实平台移植缺陷）
- 执行器两处缺陷（2026-09-20 修正）:
  ① **强制 `CRYPTSETUP_PATH` 造成假 SKIP**：`vectors-test`(`tests/crypto-vectors.c:1694`) 与
  `unit-utils-crypt-test`(`tests/unit-utils-crypt.c:229`) 有 `if (getenv("CRYPTSETUP_PATH")) exit 77`，
  加 `NOPATH` 白名单后本轮二者在同一轮内正常 PASS（单独复跑证据仍在 `upstream-testlogs-rerun/`）；
  ② **TESTS 清单漏项**：原清单 34 项，漏了条件项 `systemd-test-plugin`，补齐后**整轮重跑 35 项**，
  保证单轮自洽。
- 逐项判定与耗时均读自 `upstream-testlogs/<name>.raw.log` 的 automake 判定行
  （`PASS:`/`SKIP:`）；`summary.tsv` 的 `result` 列记的是 **make 退出码**（0=PASS，故 35 行全 PASS），
  两者口径不同、互不矛盾。


## 5b. L2 smoke（W3）三条警告的根因（非本包缺陷）

`ci/conan/build_and_test.sh` 的 L2 直接把 `$PKG_CACHE/bin/*` 逐个 `--version`，
**不注入 LD_LIBRARY_PATH**；而 OHOS musl **不解析 RUNPATH**（且本包 rpath 是构建期残值 `//lib`），
所以 `libcryptsetup.so.12` 找不到 → rc=127。复现与反证：

```
$ p/bin/cryptsetup --version                          → rc=127  Error loading shared library libcryptsetup.so.12
$ LD_LIBRARY_PATH=包lib:json-c lib:lvm2 lib … --version → 仍 127  Error loading shared library libjson-c.so.5
   （json-c 依赖包的 SONAME 文件 libjson-c.so.5 是**软链** → 该 exec 域拒载，E316/E505 同族）
$ 把 json-c 的 .so 实体化后 LD_LIBRARY_PATH 指过去       → rc=0  cryptsetup 2.8.8 flags: BLKID KEYRING KERNEL_CAPI
```

同一二进制在 conan `test_package` 里能正常跑（W3 日志 `RUN: "…/p/bin/cryptsetup" --version` →
`cryptsetup 2.8.8 flags: …`），三个二进制（cryptsetup/veritysetup/integritysetup）实体化后亦全部 rc=0
⇒ L2 的 warn 是**执行环境（缺 LD_LIBRARY_PATH + 依赖包软链 SONAME）**所致，属框架侧非阻塞项
（脚本自身标 `(non-blocking)`，`L2_RESULT=skip` 不阻塞 W3 通过）。

## 6. revision 对齐：W3 校验的是镜像形态，PR 提交的是官方形态

W3（`ci/conan/build_and_test.sh`）会把 `conandata.yml` 的 `sources.url` 单值改写成**镜像列表**
（本包映射到 ustc/tuna/nju + 官方共 4 条），因此 W3 构建期导出的 recipe 是
`cryptsetup/2.8.8#570dcc4d819cb9388b9a37f43938c97b`；而**可提交形态**（工作区/PR 里的官方单 URL）
导出为 `#2eb8f920b9955ec6d67beb044f95f5ae`。两者 revision 必然不等（revision 对 conandata 字节敏感）。

等价性闭环（三条，均已实测）：

1. 官方形态下单独强制重建：`reports/conan-create-official.log`，`Forced build from source` +
   `Package '1b79245589adf878dc26a120d2e09327bdfecae8' built`；
2. 两形态的导出内容仅 `sources.url` 一行不同（`conanfile.py` sha256 同为
   `b5674dc3…`、`sources.sha256` 同为 `3acfa685…`）；
3. **产物同一性**：官方形态包与该 W3 镜像形态包对 `conanmanifest.txt`（51 条目）逐文件比对——
   `仅在 official`=0、`仅在 w3`=0、md5 不一致=1（仅 `lib/libcryptsetup.la`，差异为该文件内嵌的
   `dependency_libs` 绝对构建路径），三个 CLI 二进制与 `libcryptsetup.so.12.11.0` 的 sha256 完全相同
   （`bin/cryptsetup` = `bdb3902d00cfbe43d30a7acfb852ac4d7169e294551bbc43129feacb42e186d2`、
   `bin/integritysetup` = `733f455c8e02d8117fd1edc940d5198d082c4ece45938140e4ac4ca3ba8b815c`、
   `bin/veritysetup` = `c4571f114c54196418f5ee39866746296d0721a151edfaf70ed60a3ba47dc015`、
   `lib/libcryptsetup.so.12.11.0` = `76bae267773f06a7d5a36c601474775ddb450b7ad3fbfd7b84a668f8d2f278eb`）。
   存证：`.workbuddy/tmp/cryptsetup-2.8.8/revcheck/conanmanifest-{official-2eb8f920,w3mirror-570dcc4d}.txt`
   与同目录 `artifact-sha256.txt`（用 `sha256sum` 实测生成）。

## 7. 已知项与待决项（提交前请知悉）

1. **补丁 0004 的 `diff --git` 头含内部工作路径**：其四处 hunk 的头行为
   `diff --git a/lib/utils_device.c b/fp-b/lib/utils_device.c`（b 侧多出框架补丁生成器的工作目录名
   `fp-b`），而 `--- a/…` / `+++ b/…` 两行是标准的，故 `git apply --check` 与 `patch -p1 --dry-run`
   均 rc=0、0 FAILED（已由独立审计复验）。此为**生成器产物**，属**美观性问题**，不影响应用与产物。
   ⚠️ 若决定修正该头行，会改动 `patches/` 字节 ⇒ recipe revision 变化 ⇒ 现有 conan create /
   conan-verify / W3 证据全部失效，须重跑全链路（约 35-40 min）。**当前按"不改"处理，等提交前确认。**
2. **`packaging/` 与 `.staging-verified` 已产出（2026-09-20 23:27 补做）**，`finish` Step 10 原有的
   2 项未就绪已消除，`submit` 6 项自检由 5/6 变为 **6/6**。两者均被 `.gitignore` 覆盖、**不入 PR**
   （`packaging/` → `.gitignore:2`；`.staging-verified` → `.gitignore:222`）。
   准确定位（读框架源码核实）：
   - `.staging-verified` 的语义是"对 staging 前缀二进制的**验证报告**"（legacy 14 步 driver 的
     `_step8_staging`，`scripts/ohc/driver.py:1086-1105`；`dispatch.py:304-321` 据此判 `built`；
     `finish.py:380-384` 只做存在性判断）。本次按同一语义**真跑**而非造空文件：自 conan 包目录搭
     干净 staging 树 → `bin/{cryptsetup,veritysetup,integritysetup} --version` 三者全 rc=0 →
     写 `verified=3 failed=0` 并附探测命令、`LD_LIBRARY_PATH` 必要性说明与时间戳。
   - `packaging/*.tar.gz` 由官方链路产出：`verify-build --install-prefix`（写 `.verify-passed`，
     verdict=PASS）→ `PackageBuilder` 10 步 → `cryptsetup-2.8.8-ohos-aarch64.tar.gz`
     （16561652 B / **60 条目** = bin 4 + include 2 + lib 9 + licenses 3 + share 42，
     sha256 `260e8441…`）与 `-debug.tar.gz`（3168759 B，sha256 `e94c3609…`）+ `.packaged`。
     ⚠️ 包内二进制 sha256 与 conan 包内**不同**（如 `bin/cryptsetup`：包内 `bdb3902d…` vs
     tar 内 `a641db32…`）——因为 `PackageBuilder` Step 7 对 ELF 做了**签名**（Step 8 另修执行权限），
     属框架预期行为。
   - **为什么没有重跑 `finish` 让它的日志一并转绿**：`finish` 重跑会 ① Step 4 内嵌 G2 因包已在缓存
     而把 `reports/conan-create.log` **重新写成"命中缓存"形态**，回退上面刚修好的真编证据；
     ② Step 8 `gen_summary` 会改写 **tracked 框架文件 `SUMMARY.md`**；③ Step 1 `refresh-patch` 会
     重新生成 `patches/`（recipe revision 敏感）。而失败步骤 `step5b` 与本任务无关、不会因重跑转绿
     （见 #7），故重跑只带来回退风险、不改变判定，**决定不重跑**，改为在此如实记录两项已达标
     （并有 `submit` 6/6 自检 + 产物 sha256/条目数存证）。
3. **仓库根 `pr.diff`** 是本次 W2 原子性检查的权威变更清单（未被 `.gitignore` 覆盖），
   **提交时必须删除或确保不被 `git add`**（本任务全程使用显式白名单 `git add`，不用 `git add -A`）。
4. **`test_package/build/`** 为 `conan create` 的构建残留（被 `.gitignore:17` 覆盖）——**已清理**；
   其中唯一的运行期断言计数证据已另行留档为 `reports/test-package-lasttest.log`
   （现为 G2 真编轮：`16 check(s) run, 0 FAILED` / `Test time = 0.54 sec`），
   静态口径可用 `grep -c '^    check(' test_package/test_cryptsetup.c`（=16）复算。
5. **`conandata.yml` 的 `patch_type` 用了 `platform` / `ohos_test`**，与 `.gitcode/code-style.md`
   §12 的"固定 `portability`"表述不完全一致；仓库现状有 `platform` 先例，故**记录不改**（改动会变更
   recipe revision 并失效全部门禁证据）。**冻结口径**（锚定提交 `3ae0ccf132`，且只统计**已跟踪**文件
   ——`git grep` 不看未跟踪文件，故不受本机并行任务新增工作区文件影响；任何人可原样复现）：

   ```
   git grep -h -E "^[[:space:]]*patch_type:" 3ae0ccf132 -- 'archives/*/*/*/conandata.yml' \
     | sed -E 's/^[[:space:]]*patch_type:[[:space:]]*"?([A-Za-z_-]+)"?.*/\1/' | sort | uniq -c | sort -rn
   ```

   → `portability` 5903 / `bugfix` 242 / **`platform` 98** / `test` 81 / `conan` 40 / `backport` 34 /
   `compatibility` 25 / `cmake` 12。
   ⚠️ 若改用裸 `grep -rhoE` 扫工作区（会连带统计**未跟踪**文件），同一命令不同时刻实测到
   `platform` 98 / 104、`bugfix` 242 / 244、`portability` 5903 / 5911 / 5912 —— **正是本机并行任务
   边写边测导致的漂移**，故本条只采用上表的 `git grep` + 冻结提交口径。
6. **`conandata.yml:51` 的「本补丁统一在 posix_fallocate 失败时退化为 ftruncate」措辞偏宽**：
   其上下文已逐条列出 4 处站点，且 §2 的站点判据表说明另两处上游本就容错，语义无误；
   但因 `conandata.yml` 属 recipe revision 敏感文件，**记录不改**。
7. **`finish` 的 `step5b`（知识图谱字段完整性）失败与本任务无关，且在本任务范围内不可修**：
   `check_knowledge_completeness` RC=1 的报错项**只有**三条他人包条目——
   `knowledge/graph/E219.kv`（python 构建环境）、`E253.kv`（OCaml 工具链）、`E305.kv`（字体资源包）
   的 `root_cause`（E305 另含 `rec_approach`）被判"为空"。实测根因：这三条用的是 YAML **块标量**
   `root_cause: |`，框架的 hash 式解析器不解析块标量 ⇒ 读到空值（文本其实非空）；
   三者 `git ls-files` 为 **tracked** 且 `git cat-file -e upstream/main:…` 存在、
   `git diff upstream/main` 为空 ⇒ **upstream 既有数据**，非本任务引入。按本任务"只处理目标库自身
   文件、禁止混入他包"的原子性约束**不得在本 PR 内改这三条**（改了就是越界 + 会变更他人证据）。
   ⇒ `finish` 会因它保持 `exit=1`，这是**框架/上游数据层**问题，不是本配方的门禁失败。
8. **框架健壮性缺口（建议反馈上游，本任务未改框架）**：`PackageBuilder.step2_copy` 在
   `src_prefix` 不存在时**静默不复制**（无 `log_fail`），`step9_tarball` 仍打印
   `✅ 打包完成` 并以 **RC=0** 结束，于是产出**空包**（实测 `--prefix` 指向不存在路径 ⇒
   2071 B / 2 条目 `lib/`、`lib/external/`，且 `submit` 的 `packaging_present` 只判
   `packaging/*.tar.gz` 是否存在、**不校验内容**，空包同样会判 `True`）。
   另有一处调用陷阱：`--project-dir` 传**相对路径**（如 `.`）会让 `packaging_dir` 变相对，
   而 `step9` 是 `tar czf <相对目标>` + `cwd=pkgdir` ⇒ 目标被解析到 pkgdir 内、`tar` rc=1，
   且 stdout/stderr 被 `capture_output=True` 吞掉，只留一行 `❌ 打包失败`。
   ⇒ **凡走 `PackageBuilder` 必须 ①传绝对 `--project-dir`；②打包后 `tar tzf` 校验条目数与体积**。
   本次产物校验存证：`.workbuddy/tmp/cryptsetup-2.8.8/revcheck/packaging-staging-evidence.txt`。
9. **`reports/` 下全部证据均为本地留档**（`.gitignore:96` 覆盖、不入 PR）：`conan-create-official.log`、
   `conan-create.log`、`conan-verify-report.md`、`test-report.md`、`w3-local-ci.log`、
   `test-package-lasttest.log`、`audit-result.json`。PR 内可复核的静态口径：`notes.md` §5/§6、
   各 `reports/*.md` 中引用的命令与行号。

构建终局: conan create 第 11 轮 EXIT=0，package_id `1b79245589adf878dc26a120d2e09327bdfecae8`；
官方形态复建（第 12 轮）EXIT=0，同一 package_id。


---

**编译结束**: 2026-09-20 19:52
**最终状态**: built
