# oomd 0.5.0 适配笔记

> 阶段：**W3 构建完成（manifest status=built）+ W4 首轮独立审计（verdict=fail：P0=0 / P1=1 / P2=4 / P3=3）整改完毕，门禁已按整改后状态复跑**。门禁与真机读数见 §13、整改对照与复跑读数见 §13.5；测试口径以 §13.1 为唯一权威（N=208 / E=204 / P=204 / F=0，未执行 A−E=4）。

## 0. 任务与环境

| 项 | 值 |
|---|---|
| 平台任务 | 9170（oomd 0.5.0，lang=cpp，diff=medium，主号名下） |
| 路径 | 路径 C（高难度挑战），资质已判定成立，**是否开跑构建待主理/用户裁定** |
| worktree | `~/qzy/主理-1-oomd-0.5.0` |
| 分支 | `feat/oomd-0.5.0`（基线 `upstream/main=255e506963`，建前已 fetch） |
| CONAN_HOME | `~/tmp/ch/home-oomd`（三步播种：mkdir → cp remotes.json → 追加 `core.sources:download_cache`；`conan remote list` 见 ohpcd ✅） |
| profile | `ci/conan/profiles/ohos-aarch64`（os=OHOS / arch=armv8 / clang 15 / libc++ / cppstd=17） |
| 环境前置 | `SSL_CERT_FILE=$HOME/usr/local/ssl/cert.pem`、`PATH=$HOME/usr/local/bin:$HOME/.local/bin:$PATH`（缺任一则 preflight/工具链误报） |

## 1. 路径 C 资质判定（源码级证据）

上游 v0.5.0 源码（`git clone --depth 1 --branch v0.5.0`；README L18-L19：
"oomd leverages PSI and cgroupv2 to monitor a system holistically"；
L43："Note that oomd requires PSI to function"）。

**命中硬资质①：强绑定 Linux 私有系统接口且无跨平台抽象层。**
oomd 没有任何 OS 抽象层 —— PSI 与 cgroupv2 的路径直接写死在 `util/Fs.cpp` 的
字符串常量与 `/proc`、`/sys` 硬编码路径里，`--cgroup-fs` 只把挂载点做成命令行
参数，读取的仍是 cgroup v2 专有文件语义。

| # | 上游文件:行 | 接口 | OHOS 实测 |
|---|---|---|---|
| 1 | `src/oomd/Main.cpp:107-124`（`system_reqs_met()`：读 `/proc/pressure/memory`，兜底 `/proc/mempressure`） | 全局 PSI memory | `/proc/pressure/memory` **可读 rc=0**，但内容 `some avg10=78.20 avg60=78.20 avg300=78.20 total=78`，`full` 行**与 some 完全相同**、`total=78`（上游按累计微秒解析）⇒ **语义与 Linux PSI 不一致**；`/proc/mempressure` **rc=1（ENOENT）** |
| 2 | `src/oomd/util/Fs.cpp:466-475`（`readRootMempressure()` → `/proc/pressure/memory`） | 全局 PSI memory | 同上，rc=0 但数值语义存疑 |
| 3 | `src/oomd/util/Fs.cpp:667-672`（`readRootIopressure()` → `/proc/pressure/io`） | 全局 PSI io | `/proc/pressure/io` **rc=1（No such file or directory）** ⇒ IO 压力路径必失败 |
| 4 | （同族）`/proc/pressure/cpu` | 全局 PSI cpu | **rc=1（Permission denied）**，`stat` 即被拒 |
| 5 | `src/oomd/util/Fs.cpp:898-912`（`getCgroup2MountPoint()` 扫 `/proc/mounts` 找 `cgroup2`） | cgroup v2 统一层 | `/proc/mounts` 139 行、**`grep -c cgroup2` = 0（rc=1）** ⇒ 返回 `SYSTEM_ERROR(EINVAL)` |
| 6 | `src/oomd/Main.cpp:121-130`（`cgroup_fs_valid()`）+ `Main.cpp:457-461`（打印 `is not a valid cgroup2 filesystem` → `EXIT_CANT_RECOVER`） | 启动硬闸 | 第 5 条成立 ⇒ **二进制即使编译成功也起不来**（"未适配前真实失败现象"，W3 后补实测 rc） |
| 7 | `src/oomd/util/Fs.h:36-56`（`kControllersFile/kSubtreeControlFile/kProcsFile/kMemCurrentFile/kMemPressureFile/kMemLowFile/kMemHighFile/kMemMaxFile/kMemHighTmpFile/kMemReclaimFile/kMemMinFile/kMemStatFile/kMemSwapCurrentFile/kMemSwapMaxFile/kIoPressureFile/kIoStatFile` 等） | cgroup v2 控制文件族 | `/sys/fs/cgroup` 是 **tmpfs**，只有 `devices/ freezer/ systemd/` 三个 **cgroup v1** 目录；`cgroup.controllers`/`cgroup.subtree_control` **ENOENT（rc=1）**；`find /sys/fs/cgroup -name memory.pressure` **0 结果**；v1 memcg 挂在 `/dev/memcg`（`Permission denied`，`memory.limit_in_bytes` ENOENT）⇒ **v2 控制文件全族缺失，v1 语义不同名** |
| 8 | `src/oomd/CgroupContext.cpp:115-209`（`readMemcurrentAt/readMemhighAt/readMemmaxAt/readMempressureAt/readIopressureAt/readSwapCurrentAt/…` 全部按 v2 文件名 `openat`） | 每 cgroup 内存/压力读取 | 同 7，OHOS 无任何可读同名 v2 文件 |
| 9 | `src/oomd/plugins/BaseKillPlugin.cpp:373`（`openat(cgroup.procs)` 取 pid）+ `:471`（`::kill(pid, SIGKILL)`） | 杀进程路径 | 需先有 v2 cgroup 树才能选中受害者；v1 树在 `/dev/memcg` 且不可访问 |
| 10 | `src/oomd/plugins/Senpai.cpp:187-464`（读写 `memory.high.tmp`/`memory.high`/`memory.max` 调节水位） | v2 内存压力反馈控制 | `memory.high.tmp` 是 **v2 独有控制文件**，v1 无对应物 |

**因此必须做的适配形态（预计，W3 后收敛）**：
1. **编译期**：`meson.build` 硬写 `link_args: ['-lstdc++fs']`（GCC 时代独立库），OHOS clang15+libc++ 实测 `ld.lld: error: unable to find library -lstdc++fs`（同 toolchain 编译+运行 `std::filesystem` rc=0，libc++ 原生提供）⇒ 补丁移除。
2. **运行期 shim / 降级路径（路径 C 主体）**：`getCgroup2MountPoint()` 无挂载点、`readRootIopressure()` 无 `/proc/pressure/io`、每 cgroup 的 `memory.*`/`memory.pressure` 全族缺失 ⇒ 要么自建 shim（把 v1 `/dev/memcg` 的 `memory.limit_in_bytes/memory.usage_in_bytes` 映射到 v2 语义、给压力读数提供降级数据源），要么做降级路径（无 cgroup2 时按插件能力开关启动、PSI 不可用时回退 `memory.stat`/`/proc/meminfo` 启发式），并深改内存与进程管理逻辑（Senpai / KillMemoryGrowth / KillPressure / PressureAbove 的判定与杀进程链）。

> 结论：**路径 C 资质成立（硬资质①）**，不是"这包比较难"的主观判断 —— 上表 10 处是
> 源码里写死的 Linux 私有接口 + 本机可复跑的 rc 读数。按 AGENTS §9，**开跑构建须经批准**。

## 2. 本机接口实测读数（2026-10-01，B 机，uid=20020084）

```text
$ ls -l /proc/pressure
-rw-rw-r-- 1 system system memory
-?????????  ? ?      ?      cpu        ← stat 即失败
（io 目录项不存在）

$ head -1 /proc/pressure/memory ; echo rc=$?
some avg10=78.20 avg60=78.20 avg300=78.20 total=78          rc=0
$ head -1 /proc/pressure/cpu    ; echo rc=$?
ls: /proc/pressure/cpu: Permission denied                    rc=1
$ head -1 /proc/pressure/io     ; echo rc=$?
ls: /proc/pressure/io: No such file or directory             rc=1
$ head -c 100 /proc/mempressure  → No such file or directory rc=1

$ grep -c cgroup2 /proc/mounts ; echo rc=$?
0                                                            rc=1
$ ls /sys/fs/cgroup → devices  freezer  systemd              rc=0（tmpfs，cgroup v1）
$ ls /sys/fs/cgroup/cgroup.controllers → No such file        rc=1
$ find /sys/fs/cgroup -maxdepth 3 -name memory.pressure → 0 结果
$ ls /dev/memcg → Permission denied；/dev/memcg/memory.limit_in_bytes → ENOENT rc=1
```

## 3. W0 读数

| 门禁 | 命令 | rc | 关键输出 |
|---|---|---|---|
| CONAN_HOME 播种 | `conan remote list` | 0 | `ohpcd: https://conan.cnb.cool/OpenHarmonyPCDeveloper/Conan/-/packages/` ✅ |
| 播种自检 | `conan config show '*' \| grep download_cache` | 0 | `core.sources:download_cache=/storage/Users/currentUser/tmp/ch/dlcache` |
| 预检 | `bash ci/scripts/preflight_check.sh oomd/0.5.0` | **0** | 配方落盘前：`未找到依赖声明…预检通过（无依赖需要检查）`；**配方落盘后复跑：`发现 3 个依赖` → gtest/1.17.0.2、jsoncpp/1.9.8、meson/1.11.0 全部 `[OK] 已发布` + `版本号未被占用: oomd/0.5.0`** |
| PF 静态闸 | `python3 scripts/ohc/preflight.py <wt> upstream/main HEAD` | 1 | PF1–PF8 + R52 全过（PF8 首轮报"CLI 包缺 commands.json"→ 移到包级后 0 条；PF1/PF2/PF5/PF6/PF7/PF8/PF3 均 0 条）；**仅剩 PF9 1 条**=包级 `commands.json` 判"缺版本目录层"，已用合入件 `tal ef6e170c9b` 复现同一误报，属已知口径互斥（见 §8 第 4 条） |
| 配方检索 | `ohc-run.py recipe-search oomd` | **0** | catalog 重建 7920 配方 → `无相似配方（语料 7919 条）——首稿走 conan-init 模板` |
| 依赖快查 | `pipeline.py depcheck oomd 0.5.0` | **0** | 仅提示"备注提到依赖但未标等依赖"（备注文本误触发，**非真实上游阻塞**） |
| 依赖二进制（W0 硬门） | `conan install --requires=<dep> --build=never -pr:h/-pr:b=ci/conan/profiles/ohos-aarch64` | **0 / 0 / 0** | `jsoncpp/1.9.8` ✅、`gtest/1.17.0.2` ✅、`meson/1.11.0` ✅ —— 三者均从 ohpcd 拉到**预编译二进制**，`Install finished successfully` |
| 参考探测 | `conan download "cmake/*"/"make/*"/"libsystemd/*" -r=ohpcd --only-recipe` | 0 | 各 **0 匹配** ⇒ CI 用系统 cmake/make；**libsystemd 无** ⇒ 上游 optional 依赖自然关闭 |
| worktree | `git worktree add -b feat/oomd-0.5.0 … upstream/main` | 0 | HEAD=`255e506963`；`status --porcelain` = 2 行（`archives/l/libXext/{README.md,manifest.yaml}` HMDFS 幻影，**不提交**） |

**依赖结论：无未发布依赖，不需要 `$P block` 转手**（jsoncpp / meson / gtest 全部在制品仓且有 OHOS 二进制）。

## 4. 测试口径（静态统计，W3 实测后回填运行数）

- **上游入口**：`.github/workflows/ci.yml` = `meson build/ && ninja -C build/ && ninja -C build/ test`。
- **上游套件**：顶层 `meson.build` 的 `core_tests` = **12 套件 / 207 例**（gtest，`TEST/TEST_F/TEST_P` **静态宏**统计；其中 1 个 `TEST_P` 由 `INSTANTIATE_TEST_CASE_P` 展开 **2** 例 ⇒ **运行期发现总数 N=208**，最终口径以 §13.1 为准）。
- **本平台可编译套件**：**11 套件 / 205 例（静态宏数；运行期实测 206 例 = 204 PASSED + 2 SKIPPED，见 §13.1）** —— 第 12 套件 `systemd_plugin`（2 例）依赖 `dependency('libsystemd')`，制品仓无该包 ⇒ 上游自身条件编译即不包含，属"跳过项（技术原因：可选依赖缺失）"。
- **断言数**：全量 18 个测试文件 `EXPECT_*/ASSERT_*` 共 **1163**；扣 systemd 套件 8 处 = **1155**。
- **依赖真实宿主环境的用例**：`CgroupContextTest.MonitorRootHost`（读真实 cgroup2 挂载点；上游自带 `GTEST_SKIP` 分支）。其余 **204 例（静态口径；运行期 205 例）均基于内存 fixture**（`fixtures/FsFixture.cpp` 合成 cgroup 树），**不需要真实 cgroup**。
- **鸿蒙特有测试（拟新增，W3 后定稿）**：真机执行 `oomd --help` 契约 + ELF/链接断言（test_package `test.sh`，10 断言）；另记录"无 cgroup2 时启动路径的真实失败/降级表现"实测 rc。

## 5. 配方骨架（已落盘，未构建）

```text
archives/o/oomd/0.5.0/
├── conanfile.py          # meson + PkgConfigDeps；requires jsoncpp/1.9.8；
│                         # tool_requires meson/1.11.0；test_requires gtest/1.17.0.2
│                         # build(): meson setup → compile → meson test（上游官方入口）
├── conandata.yml         # 源 URL + 实测 sha256（patches 段暂空）
├── commands.json         # PF8 门禁：application 包必带，type=tool（binary=false，发布后翻 true）
├── manifest.yaml         # status: pending（W3 后由 finish 置 built）
├── notes.md              # 本文件
├── patches/              # 暂空（0001 待生成）
└── test_package/
    ├── conanfile.py      # 真实执行打包产物（wmname 0.1 先例）
    ├── test.sh           # 10 断言：--help rc=0 / usage / --cgroup-fs / ELF64·LE·AArch64 /
    │                     #  DT_NEEDED 真链 jsoncpp / 配置与 man 随包安装
    └── MANIFEST.yml      # 11 套件静态 205 宏（运行期 206 例）上游声明 + 断言数 1155
```

## 6. 预计补丁与风险（未实测，仅按已验证事实推断）

| # | 预计补丁 | 依据（已有读数） | 状态 |
|---|---|---|---|
| 1 | `meson.build` 移除 `-lstdc++fs` | OHOS clang15 实测 `ld.lld: error: unable to find library -lstdc++fs`；同 toolchain 编译+运行 `std::filesystem` rc=0 | **已确证**，待生成 patch 文件 |
| 2 | `CgroupContextTest.MonitorRootHost` 无 cgroup2 时按上游意图走 `GTEST_SKIP` | `getCgroup2MountPoint()` 返回 `SYSTEM_ERROR(EINVAL)` 而非空串，`ASSERT_SYS_OK` 会先判失败 | **待 W3 实测**（若上游分支确能跳过则不需补丁） |
| 3 | 运行期 PSI/cgroup2 降级（shim 或能力开关） | §1 表第 1-10 条 | **路径 C 主体**，构建通过后再定形态 |

停损口径：同一错误类别连续 2 轮红即停（附首条真实错误 + 完整命令 + rc + 关键环境）。

## 7. 编译环境

- 构建系统：meson（MesonToolchain + PkgConfigDeps；命令行手动 `meson setup/compile/test`，c-json 1.0.0 先例）
- 编译日期：2026-10-01（待 W3）
- 编译器：clang/clang++ 15.0.4（`aarch64-unknown-linux-ohos`）
- 状态：pending

## 8. 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `conan download <pkg>/ -r=ohpcd` 报 `Max retries exceeded` | 搜索端点 `?q=<pkg>/` 对空版本串不友好 | 改用 `<pkg>/*` 通配（`conan download "jsoncpp/*" -r=ohpcd --only-recipe` 成功） |
| 2 | `init-archive` 提示 conanfile/conandata/test_package 模板不可用 | 模板文件名 `conanfile-meson.py.tmpl` 与工具查找名不匹配 | 手写骨架（照 `archives/c/c-json/1.0.0` 与 `templates/test_package-executable` 先例）；工具缺陷另报，不自行改框架 |
| 3 | `conan config show` 无参报错 | conan 2.x 需要 pattern 参数 | `conan config show '*'` |
| 4 | PF8 要求 `commands.json` 在**包级**（`archives/o/oomd/commands.json`），PF9 却把包级路径判为"缺版本目录层" | 两闸口径互斥：PF8 读 `pkg_dir/commands.json`（`_pkg_dirs` 正则只取到包层），PF9 要求所有变更路径 ≥5 段 | **保留包级**（PF8 与仓库主流口径：全仓 3448 个包级 vs 17 个版本级；近一周合入的应用包 tal / wmname / communicator / toybox / ohcount / memstat **全部是包级**）。实测复核：对已合入的 tal 提交 `ef6e170c9b` 跑同一闸，同样报 PF9（3 条）却已合入 ⇒ 属**已知误报**；且 `$P create-pr` 走的是 pipeline 自己的 rule5 白名单（只允许 `archives/`、`knowledge/drafts/`），不经过 `scripts/ohc/preflight.py`，CI 侧亦未拦。留档待报幕僚 |

## 9. 依赖版本

- jsoncpp/1.9.8（运行期；pkg-config 名 jsoncpp；产物 `libjsoncpp.so`）
- meson/1.11.0（构建期 tool_requires）
- gtest/1.17.0.2（构建期 test_requires；自带 gtest / gtest_main / gmock / gmock_main 四个 `.pc`）
- libsystemd：**不依赖**（上游 optional，制品仓无此包）

## 10. 验证结果

```bash
# 第一阶段（W0 + 配方骨架阶段）实测：
preflight_check.sh oomd/0.5.0                                     → rc=0
ohc-run.py recipe-search oomd                                     → rc=0（无相似配方）
pipeline.py depcheck oomd 0.5.0                                   → rc=0
conan install --requires=jsoncpp/1.9.8  --build=never -pr:h/-pr:b → rc=0
conan install --requires=gtest/1.17.0.2  --build=never -pr:h/-pr:b → rc=0
conan install --requires=meson/1.11.0    --build=never -pr:h/-pr:b → rc=0
# W3 及以后（conan create / conan-verify / finish built / graph validate）见 §13
```

## 11. 注意事项

- 提交只 `git add -- archives/o/oomd/0.5.0/`：`archives/l/libXext/*`（HMDFS 幻影）、`.build-cache/`、`pr.diff` 一律不进。
- 临时文件一律落 `~/tmp/uc2/oomd-0.5.0/`（`/tmp` 只读）。
- PR 标题固定 `【高难度挑战】feat(oomd): 0.5.0 适配 HarmonyOS PC`；正文不建知识草稿、不建 Issue（路径 C 非 B 交付物）。

## 12. W3 构建轮次实测记录（r1–r7，首条真实错误 + 处置）

> 全部命令同一条：`conan create archives/o/oomd/0.5.0 -pr:h/-pr:b=ci/conan/profiles/ohos-aarch64 --build=missing`
> （经 `build-slot.sh --wait 1800 --mem 2500 --kind short` + `gate.sh 5000` 双闸）；
> 日志 `~/tmp/uc2/oomd-0.5.0/create-r{N}.log`；CONAN_HOME=`~/tmp/ch/home-oomd`。

| 轮 | rc | 首条真实错误（原文） | 根因类别 | 处置 |
|---|---|---|---|---|
| r1 | 1 | `../src/oomd/StatsClient.cpp:143:9: error: unknown type name 'timeval'`；链接期 `ld.lld: error: unable to find library -lstdc++fs` | glibc 传递包含在 musl 不成立；GCC 时代 link_arg | 0001 / 0002 |
| r2 | 1 | `Fs.cpp:212:29: error: use of undeclared identifier 'GLOB_BRACE'`（`GLOB_ONLYDIR` 同） | GNU 扩展宏，musl `glob.h` 无 | 0004 |
| r3 | 1 | `Util.cpp:230:15: error: no matching constructor for initialization of 'std::string'` + `Fixture.cpp:86 invalid operands ('std::string' and 'int')` + `Main.cpp:210 no member named 'open'` | `strerror_r` XSI(返回 int) vs GNU(返回 char*)；缺 `<fcntl.h>/<sys/stat.h>` | 0005 / 0006 |
| r4 | 1 | `Failed to apply patch: 0005-… hunk no.1 doesn't match … expected '#include <sys/un.h>' actual '#include <sys/time.h>'` | **流程自伤**：0005 按干净源码生成，把 0002/0003 的改动算进 hunk | 按 base=0001–0004 重出 0005；改用 **conan 同款 patch_ng(strip=0,fuzz=False)** 复跑，10/10 与工作副本逐字节一致 |
| r5 | 1 | `CgroupContextTest.cpp:68: Failure Value of: x Actual: false Expected: true`（`[Fs.cpp:919] /proc/mounts: Invalid argument`）；另 context/log/stats 共 4 套件败 | 三合一：无 cgroup2 / 无 GLOB_BRACE / **`/tmp` 只读 erofs**（`test -w /tmp` = NOT writable） | 0007 / 0008 / 0009 + 配方测试期显式 `TMPDIR=<build>/test-tmp` |
| r6 | 1 | `[Stats.cpp:123] Error binding stats collection socket: Operation not permitted`（stats_tests 5 例） | 沙箱**拒绝文件系统 AF_UNIX**：探针 `bind()` 在 HOME 长/短路径、cwd 相对路径、`.cache` 全 EPERM(1)，`/data/local/tmp`/`/dev/shm` EACCES(13)，**抽象 STREAM bind OK**、抽象 DGRAM EACCES(13) | 0010 抽象命名空间回退（服务端/客户端/测试三处，两端 addrlen 同源计算） |
| r7 | 1 | `stats_tests TIMEOUT 300.08s killed by signal 15 SIGTERM`；stderr `Error: connecting to stats socket: No such file or directory` | 0010 只在 **EPERM** 时回退；服务端已成功绑定抽象名，客户端首连返回 **ENOENT**（文件系统路径无该文件）⇒ 未回退 ⇒ `~Stats()` 中 `closeSocket()` 连不上 ⇒ `stats_thread_.join()` 永久阻塞在 `accept()` ⇒ 超时 | **主理裁 (A) 批 r8**（第二次也是最后一次无条件停损线）：0010 客户端侧两处触发条件放宽，**断言与分母不动** |
| r8 | 1 | `StatsTest.cpp:123: Failure Value of: msg_opt Actual: true Expected: false`（套件汇总 `Ok:10 Fail:1 Timeout:0`；stats_tests `FAIL 0.43s`） | **OHOS 套接字 close 语义差异**：`InvalidRequests` 的 `"ysdf\nasdf"` 用例靠「服务端 close() 时接收缓冲仍有未读数据 ⇒ Linux 发 RST ⇒ 客户端 read 得 ECONNRESET ⇒ msg_opt=nullopt」通过；本机探针 `probe3-rst.c` 连跑 5/5 **客户端都读到 13 字节响应** ⇒ OHOS 不因未读数据 RST ⇒ 断言反相。**非本适配引入、非功能缺陷**（同套件其余 5 例全过，BasicStats/BasicGetAndClear/LongJson/MultiThreadedMany 均绿） | **按主理第二次无条件停损令停下待裁**。可选修法：B1 忠实复刻 Linux（服务端 close 前 FIONREAD>0 则 `SO_LINGER{1,0}` 强制 RST，断言零改动、可回到 Ok:11）｜B2 对该单例 `GTEST_SKIP`+上游意图注释（当时的早期口径 E=206/207，分母不缩；**最终口径见 §13.1：N=208 / E=204 / P=204 / F=0**）｜B 收口交接 |

**单调向好读数**：编译自 r5 起 75/75 全过；上游套件 r5 `Ok:7 Fail:4` → r6 `Ok:10 Fail:1` → r7 `Ok:10 Fail:0 Timeout:1`。

### 12.1 r8 触发条件的准确口径（主理 ②-2 要求原文）

> **文件系统 connect 失败（任一 errno）⇒ 回退抽象命名空间；服务端仅 EPERM 回退。**

- 服务端 `Stats::startSocket`：`bind()` **仅当 `errno == EPERM`** 才退到抽象命名空间 ——
  这样 `StatsTest.InvalidSocketPath`（路径 `/var/`，`unlink` 即失败）的**期望抛错**语义不变，
  ⛔ 不放宽成"任意失败都回退"，否则那个用例会变成静默回退 = 改断言效果。
- 客户端 `StatsClient::msgSocket` 与 `StatsTest.MultiThreadedMany`：文件系统 `connect()`
  **任意失败**（沙箱 `EPERM`，或服务端已退抽象导致路径无节点的 `ENOENT`）都退到抽象命名空间。
- 两端都用 `Stats.h` 里同一对 `fillAbstractUnixAddr()` / `unixAddrLen()` 派生地址，
  保证抽象名与 addrlen 逐字节一致（抽象名对 addrlen 敏感，长 addrlen 会多拼 NUL 改名）。
- 验证口径：conan 同款 `patch_ng(strip=0, fuzz=False)` 按序 **10/10** 且 `src/`+`meson.build`
  与工作副本逐字节一致；受影响 TU 本地 `-fsyntax-only` **9/9 = 0 error 0 warning**。
- **绿的定义（r8）**：`Ok: 11 / Fail: 0 / Timeout: 0` —— `stats_tests` 必须真跑出结果，
  不许超时、不许用 `GTEST_SKIP` 跳过（这是功能真修，不是受限跳过）。

### 12.2 r8 残余失败的性质取证（停损上报用）

- 失败点：`StatsTest.InvalidRequests` 第 3 个子块（消息 `"ysdf\nasdf"`），`ASSERT_FALSE(msg_opt)`。
- 上游为何期望「无响应」：服务端 `processMsg` 只读到首个 `\n`（5 字节）就返回并 `close()`，
  **接收缓冲里还剩 `asdf\n` 未读** ⇒ Linux 上 `close()` 带未读数据会发 **RST**，已写出的响应被丢弃，
  客户端 `read()` 得 `ECONNRESET` ⇒ `readFull<0` ⇒ `msg_opt = nullopt` ⇒ 断言通过。
- OHOS 实测（`~/tmp/uc2/oomd-0.5.0/probe3-rst.c`，同构场景：读 5 字节→写响应→close）：
  **连跑 5/5 次客户端都读到 13 字节 `RESPONSE-JSON`**，无 RST、数据不丢 ⇒ 断言反相。
- 结论：**平台内核语义差异（close-with-unread-data 是否 RST）**，与本次 10 枚补丁无关
  （该路径只经 connect/write/read/close，我们只改了「连接失败回退抽象」）；同套件其余 5 例全绿。
- 附带观察：stderr 还有一条 `[Stats.cpp:126] Error binding stats collection socket: Invalid argument`
  来自**空路径**的抽象 bind（`Stats::get()` 默认参数 `""`，`fillAbstractUnixAddr(""` → 名长度 0 → EINVAL），
  属静态包装入口的既有行为，**未导致任何用例失败**。

### 12.3 r8 之后的授权链与 probe4 裁定（主理 ⑤ 要求记账）

**授权链**：r7 红 → 主理**批 r8**（第二次也是最后一次无条件停损线）→ r8 红（`Ok:10 Fail:1 Timeout:0`）
→ **第二次无条件停损已执行** → 主理裁 **(1) 零构建探针 probe4 先行**、**(2) B1 预案**、**(3) B2 预授权兜底**、
**(4) 走完 B1/B2 直接进阶段二、无需再点头**。以上均为**主理明示裁决的例外**，非本链自行续跑。

**probe4-linger.c 判定（零构建，未跑 r9/B1）**：

| 探针 | 服务端动作 | 结果 | 次数 |
|---|---|---|---|
| `probe3-rst.c` | 读 5 → 写 13 字节响应 → close（缓冲仍有 5 字节未读） | 客户端**读到 13 字节响应**（无 RST） | 5/5 |
| `probe4-linger.c` | 同上 + `FIONREAD=5` → `setsockopt(SO_LINGER,{1,0})` → close | `setsockopt rc=0 errno=0`、`close rc=0 errno=0`，客户端**仍读到 13 字节响应** | 3/3 |

⇒ **B1（强制 RST）在 OHOS AF_UNIX 上不可行** ⇒ 按主理②的判定分支「probe4 仍不 RST ⇒ 直接上 B2，不跑 r9」执行 **B2**：

- `patches/0011-stats-test-skip-unreproducible-rst.patch`：仅在 **`msg_opt` 确有响应时** `GTEST_SKIP()`，
  注释完整引用上游意图（Linux `close()` 带未读数据 ⇒ RST 丢弃已写响应 ⇒ 期望 `nullopt`）与
  两份探针文件名与次数；**`ASSERT_FALSE(msg_opt)` 原样保留、分母不缩**（B2 授权当时按静态宏记 207，运行期发现数 N=208，最终口径见 §13.1）。
- 口径（B2 授权当时的早期估算）：**E = 206 / 207**（跳过只进 E，不进 Fail）；**最终口径以 §13.1 为准：N=208 / E=204 / P=204 / F=0、未执行 A−E=4**，逐条技术原因进正文第 3 类表格。
- 验证：conan 同款 `patch_ng(strip=0, fuzz=False)` 按序 **11/11 OK** 且 `src/`+`meson.build` 与工作副本逐字节一致；
  `StatsTest.cpp` 受影响 TU `-fsyntax-only` rc=0、0 error。
## 13. 阶段二实测记录（conan-verify → finish → graph validate）

### 13.1 测试口径最终读数（修正 §12.1 的早期估算）

| 指标 | 值 | 依据 |
|---|---|---|
| 上游发现总数 **N** | **208** | 静态 `TEST/TEST_F/TEST_P` 宏 207 个 + `KillMemoryGrowthConsistentWithPreference.SizeThreshold` 为 `TEST_P` 且 `INSTANTIATE_TEST_CASE_P` 展开 **2** 例（实测 plugin 套件运行期 75 vs 静态 74）；`11 套件运行期 206 + systemd 套件 2 = 208` |
| 当前架构适用数 **A** | **208** | 全部上游用例均适用（分母不缩） |
| 实际执行数 **E** | **204** | `meson test` 实测 `11 套件 206 ran = 204 PASSED + 2 SKIPPED`；GTEST_SKIP 按主理口径不进 E |
| 通过数 **P** | **204** | `[  PASSED  ]` 合计 204 |
| 失败数 **F** | **0** | `Ok: 11 / Fail: 0 / Timeout: 0` |
| 未执行 A−E | **4** | ①② `systemd_plugin` 2 例（制品仓无 libsystemd，上游条件编译不注册）③ `CgroupContextTest.MonitorRootHost`（无 cgroup2，上游本意跳过，补丁 0009）④ `StatsTest.InvalidRequests`（AF_UNIX close 语义，探针取证，补丁 0011） |
| 执行覆盖率 E/A | **204/208 = 98.08%** | ≥90% |
| 执行通过率 P/E | **204/204 = 100%** | |

鸿蒙特有测试（test_package `test.sh`）**10/10**，不计入上游 N。

### 13.2 门禁读数

| 门禁 | rc | 关键输出 |
|---|---|---|
| `conan-verify oomd 0.5.0`（独立跑） | **0** | `G1/G0/G2/G3 PASS`、`✅ 配方验证通过: oomd 0.5.0`；G2 为干净 `conan create … --user=ohpcd --channel=stable`（含上游 11 套件 + test_package） |
| `conan create`（b4，本包全链） | **0** | `test_package: 10/10 断言通过` |
| `finish … built`（`_SKIP_PATCH_GENERATION=true`） | 1（**关键产物全部达成**，见下） | `✅ conan-verify 通过`、`✅ 本地 CI 模拟通过`（`JC_RESULT=pass`、`L0_RESULT=pass: all checks passed`）、`✅ graph validate 通过`、`EXIT_REASON: finish_success`；manifest `status: pending → built`；`.ci-result.json` 写入 `exit_code: 0` |
| `graph validate`（finish 内已过） | 0 | `doc↔kv 配套完整 (542 对)`、`✅ graph validate 通过` |

**finish rc=1 的三条失败步及其性质（均为工具/基线侧，非本包缺陷）**：
- `step7 PR 原子性`：按 `origin/main`（**fork 基线落后 upstream/main 数千提交**）比对 ⇒ 报「框架文件变更 + 配方文件变更 24885 个」——与 AGENTS §8 记载的基线过期假阳性同型；本包真实变更仅 **19 个文件**（`git diff upstream/main...HEAD`）。
- `step5b 知识完整性`：报 `E219/E253/E305.kv root_cause 为空` —— 这三条是**共享知识图谱既有条目**（542 对 doc↔kv 中的存量），非本包引入；路径 C 不交付知识草稿。
- `step8 gen_summary`：`'str' object has no attribute 'append'` —— **框架工具缺陷**（只报不改，转幕僚立档）。
- `step10 submit 就绪预检` 提示缺 `reports/test-report.md`/`packaging/`/`.staging-verified`：前两者是 `.gitignore` 显式忽略项、**不在 PR diff 内**；`.staging-verified` 若创建会被 `junk_check` 的 **JC1/JC5** 判为运行时状态文件（实测 libbfio/thc 两例即此）⇒ **不创建**。本流程走 `$P create-pr`，不走 `ohc submit`。

### 13.3 关键动作与回滚

- **`JUNK_PR_DIFF=~/tmp/uc2/oomd-0.5.0/pr.diff`**：本地 W3 CI 的 `junk_check` incremental 模式用 `origin/main...HEAD`（陈旧 fork 基线）⇒ 首轮报 `JC6 1734 个软件包`、`JC1/JC5 抓到他人 .staging-verified`；对齐本包 19 文件的 pr.diff 后 **`JC_RESULT=pass`**（AGENTS §1/§8 明示口径）。
- **conan-verify 的 E017 镜像注入会写回 `conandata.yml`**（`gh-proxy.com` + 官方双 URL）。PF7 源 URL 闸明示「conandata 只写上游官方源 URL，镜像回退由 CI 自动处理」⇒ **已还原为单一官方 URL**（还原后与已提交版本零差异）。

### 13.4 真机运行取证（PR 正文第 4 节素材，`runtime-evidence.txt`）

| 命令 | rc | 输出原文（节选） |
|---|---|---|
| `oomd --help` | **0** | `usage: oomd [OPTION]...` |
| `oomd --version` | **0** | `v0.5.0` |
| `oomd`（默认，非 root） | **1** | `open: Permission denied` / `Unable to open outfile /dev/kmsg, not logging` / `Logging failed to initialize. Try running with sudo` |
| `oomd --kmsg-override <可写> --runtime-dir <可写>` | **3**（`EXIT_CANT_RECOVER`） | **`/sys/fs/cgroup is not a valid cgroup2 filesystem`** ← 路径 C 核心证据（`Main.cpp:457-461` 启动硬闸） |

### 13.5 W4 首轮审计整改记录与门禁复跑读数

**W4 首轮判决**：`reports/audit-result.json`（14616 B，绑定 HEAD `6efb0bc972e73094fe7cf96e038ce9926ba0b86b`）`verdict=fail`，**P0=0 / P1=1 / P2=4 / P3=3**；其「B2 合法性」单列结论为 **成立、非降 N 凑数**（0011 零删除行、`ASSERT_FALSE` 为未修改上下文、分母独立数 207 静态宏 + TEST_P 展开 2 = 208）⇒ **本轮不改任何测试代码、分母、断言与用例**，只改申报文本。

#### P1 — `manifest.yaml` `test_results` 与本文件 §13.1 互斥（改前 → 改后）

| 处 | 改前 | 改后（与 §13.1 同口径） |
|---|---|---|
| `manifest.yaml` `total` | `207` | `208` |
| `manifest.yaml` `passed` | `206`（把 2 例 GTEST_SKIP 计入 passed） | `204` |
| `manifest.yaml` `failed` | `0` | `0` |
| `manifest.yaml` `skipped` | 该键缺失 | `2` |
| 本文件 §13.1 `N/E/P/F` | `208 / 204 / 204 / 0` | 未改（权威口径） |

manifest 注释内同时写明核对式：**208 = 204 passed + 0 failed + 2 skipped + 2 条件编译未注册（`meson.build:156`，制品仓无 libsystemd）⇒ A−E = 4**（= skipped 2 + 未注册 2），与 §13.1「未执行 A−E = 4」逐条同值；`skipped` 只记实测 `[  SKIPPED ]` 的 2 例，**未注册的 2 例不进 skipped、更不进 passed**。

#### P2-1 — 同 PR 内三处旧分母「N=207」（改前 → 改后）

| 文件 | 改前原文（关键片段） | 改后原文（关键片段） |
|---|---|---|
| `patches/0011-stats-test-skip-unreproducible-rst.patch` 注释 | `the test stays in the` / `N=207 denominator and is reported as not-executed with this reason.` | `the test stays in the` / `N=208 denominator (207 static macros, one TEST_P instantiated twice) and is` / `reported as not-executed and never counted as passed.` |
| `conandata.yml` `patch_description`（0011） | `the test stays in the N=207 denominator as not-executed` | `the test stays in the N=208 denominator (207 static macros, one TEST_P instantiated twice) as not-executed, never counted as passed` |
| `manifest.yaml` `test_results` 注释 | `total = 上游发现总数 N（12 套件静态统计 207…）` / `E=P=206` | `total = 上游发现总数 N = 208 = 静态宏 207 + TEST_P 展开 2…` / `E=P=204` |

0011 补丁结构自证：新增行 **16 → 17**、hunk 头 `@@ -120,6 +120,22 @@` → **`@@ -120,6 +120,23 @@`**、**删除行仍为 0**、`ASSERT_FALSE(msg_opt)` 仍是未修改上下文行；对 pristine 源顺序实跑 **11/11 OK**，conan `apply_conandata_patches` 随 G2 复跑亦通过。

**其余自称 N/E/P 处一并消歧（全部标注「静态宏 vs 运行期发现」，不改数值语义）**：`conanfile.py` 文档串（`上游 12 套件静态 207 宏、运行期发现 N=208`）与 `build()` 注释（`静态 205 宏 / 运行期 206 例`）；本文件 §4 L91/L92/L94、§5 L113、§12 r8 表 L183、§12.3 L234-L235（均注明「早期口径，最终以 §13.1 为准」）；`test_package/MANIFEST.yml` L15-L16（`12 套件静态 207 宏 / 运行期 N=208`）。

#### P2-2 — 顶部陈旧横幅（改前 → 改后）

- 改前（原 L3，原文留档在提交 `6efb0bc972e73094fe7cf96e038ce9926ba0b86b`）：仍是开档时的「第一阶段」横幅，自称构建未开始、W3/W4 读数未回填 —— 与本文件 §12/§13 直接矛盾。
- 改后（现 L3）：见本文件第 3 行 —— 状态改为 `status=built`，并显式指向 §13 / §13.1 / §13.5。

#### 门禁复跑读数（2026-10-01 06:42–06:54，B 机）

| 门禁 | 读数 |
|---|---|
| `conan-verify oomd 0.5.0` | **rc=0**（G1/G0/G2/G3 PASS、`✅ 配方验证通过: oomd 0.5.0`）；G2 真跑 `conan create` —— 本次 `meson-logs/testlog.txt` 实测 **`[       OK ]` 204 行 + 2 例 `[  SKIPPED ]`**（`CgroupContextTest.MonitorRootHost` / `StatsTest.InvalidRequests`）、`Ok: 11 / Fail: 0`、`test_package: 10/10 断言通过` |
| conandata 还原 | `conandata.yml == .ghfast-bak == .orig`，**md5 `ac21395d1b65e1552ea5f6d6e5dbc6c1`**，镜像 URL 命中 **0**，`source.url` 单一官方 tag 归档（提交后与 HEAD 同值） |
| `finish oomd 0.5.0 built`（`_SKIP_PATCH_GENERATION=true`） | 进程 **rc=1**（失败步仍为既有的 step5b/step7/step8，与首轮同型、非本包引入）；关键产物全达成 —— `.ci-result.json` **`exit_code: 0`**，**`integrity_hash = e877ace6595727fb`**（按 `finish.py:251` 复算 `sha256('2026-10-01T06:53:33.442379:oomd:0.5.0:0')[:16]` 一致），**`log_sha256 = 1837540e5fb4e9ec0eb9766fb7ccbd043bebe04a73313626033f05509502f484`**（按 `sha256(reports/w3-local-ci.log)` 复算一致） |
| `graph validate` | **rc=0**，`doc↔kv 配套完整 (542 对)`、`All checks passed (170 warnings)` |

---


**编译结束**: 2026-10-01 06:48
**最终状态**: built
