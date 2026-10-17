- **三方库名称**：rtapd
- **上游版本**：1.7
- **上游仓库地址**：https://sourceforge.net/projects/rtnppd/ （源码包 `https://downloads.sourceforge.net/rtnppd/rtapd-1.7.tar.gz`，sha256 `cb10617032d7e3da23b3e7fe153aeb1751ac6a559fc43725b9ba5fe91296ddd7`）
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent（SKILL.md v12.22）；环境与提交流程参考 `ohos-conan-gate-env`、`ohos-conan-fork-pr-submit`

> rtapd 是 rtnppd 套件中的 TAP/TNPP 寻呼守护进程：从 rtnppd 接收到 TNPP 寻呼包（AF_UNIX 外部队列），
> 重组 TAP 页面块，按路由表投递到串口调制解调器、文件、过滤程序或其他 TNPP 地址。同一源码包构建 `vsnppd`。
> 上游为 2001 年 CVS 快照、纯 Makefile 工程（无 configure），默认构建不启用任何 SQL 后端（零外部依赖）。

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游无测试框架、源码包内无测试源文件 |
| 集成测试 | 0 | 源码包无 `tests/` 目录 |
| 其他测试 | 0 | `Makefile` 目标仅 `default/rtapd/vsnppd/*.o/clean/install.config/install`，**无 `check`/`test`**；第三方佐证：Alpine aports 的 rtapd APKBUILD 显式声明 `options="!check"` |
| **合计** | **0** | 上游无自动化测试入口 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游本无单元测试，未凭空新增 |
| 集成测试 | 0 | 不变 | — |
| 鸿蒙特有测试 | 10 | **新增 +10** | `consumer.ohos.*` 消费者用例，共 30 个检查点；在真实 aarch64 OHOS 主机上原生执行 |
| **合计** | **10** | **+10** | |

鸿蒙消费者用例逐项（`test_package/test.sh`，日志 `reports/test-report.md` 第二节）：

| # | 用例 | 断言的平台机制 |
|---|------|----------------|
| 0 | `consumer.ohos.sandbox_dir` | **OHOS 沙箱目录策略**：用真实 `bind()` 探测出允许 AF_UNIX 的目录（首轮 CI 失败后的修复点，见"补充说明"第 7 条） |
| 1 | `consumer.ohos.rtapd_usage_exit_code` | ELF 在 OHOS 上真实加载运行；getopt/usage/`exit(1)` |
| 2 | `consumer.ohos.rtapd_missing_config_exit2` | 配置错误路径退出码 = 2 |
| 3 | `consumer.ohos.vsnppd_usage_exit_code` | 第二个打包二进制可运行 |
| 4 | `consumer.ohos.daemon_boot_foreground` | `-d/-s/-x/-p` 前台启动，日志出现 `Entering into main loop` 且进程未随即退出 |
| 5 | `consumer.ohos.daemon_bind_unix_socket` | **OHOS 上 AF_UNIX SOCK_DGRAM `socket()`/`bind()`**；pid 文件为合法数字且指向真实存活进程 |
| 6 | `consumer.ohos.config_parse_dump_override` | `-p` 配置转储反映沙箱覆盖项（7 项） |
| 7 | `consumer.ohos.tnpp_cap_page_end_to_end` | **端到端**：消费者客户端 → socket → TNPP 解析 → CAP 页面 → 路由 → 文件设备落盘 |
| 8 | `consumer.ohos.cap_page_id_hex_format` | **直接验证本次补丁**：日志出现 `CAP page packet to '!1234ABCD'`，且不得出现被截断的 `'!'` |
| 9 | `consumer.ohos.sigterm_graceful_exit` | 信号处理（`sigaction`）在 OHOS 生效并退出（日志 `Exiting from main loop`） |

用例 0/4/5/6/7 断言的是**平台机制本身**（OHOS 的沙箱 unix socket 目录策略、AF_UNIX 数据报套接字、
musl 的格式化行为、信号语义），在 Linux/glibc 上无法等价通过，故可作为鸿蒙适配的证伪手段。

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 上游不存在测试用例，因此不存在"修改上游测试"的情形；本次新增的消费者用例全部位于 `test_package/`，
> 未触碰上游源码树的任何测试文件。补丁只改 `rtapd.c` / `vsnppd.c` 的可移植性缺陷（见"补充说明"）。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：为核心链路补 10 个消费者用例 / 30 个检查点 —— 覆盖可执行文件加载与退出码、
  AF_UNIX 外部队列套接字绑定（含沙箱目录策略探测）、配置文件解析与转储、TNPP 包解析与 CAP 页面路由落盘、信号处理。
> - **补全原因**：上游是 2001 年 CVS 快照，无测试框架、无 `tests/` 目录、Makefile 无 `check`/`test` 目标
>   （Alpine 亦以 `options="!check"` 跳过），因此 CI 的 L1 只能靠 `test_package` 提供真实测试；
>   同时本包为**常驻守护进程**，`--version`/`--help` 类冒烟探针不适用，必须以"沙箱内起进程 + 外部客户端驱动 +
>   断言可观测副作用"的方式验证平台可用性。
> - **新增测试文件清单**：
>   1. `test_package/conanfile.py` — 消费者测试驱动（`test_type="explicit"`；用 OHOS 工具链编译 C 客户端，再在 `conanrun` 环境跑 `test.sh`）
>   2. `test_package/check_rtapd.c` — **消费者 C 客户端**：扮演 rtnppd，按 rtapd 自身的 TNPP 线上格式
>      （SOH/字段/STX/ETX + CRC-16/ARC）向 `ExtSocketIn` 投递 CAP 页面块；
>     另提供 `--pick-sockdir`，用真实 `bind()` 探测可用的沙箱目录
>   3. `test_package/test.sh` — 沙箱驱动脚本：自包含沙箱内以前台方式启动守护进程，串起上述 10 个用例
>   4. `test_package/MANIFEST.yml` — 上游测试清点结论与适配后用例声明（`upstream_tests: []`）

## 验证结果

- 编译状态：**通过**（`conan create` 清空本地缓存后全量重建：`Building from source` + 4 个编译单元
  （rtapd.o/readcfg.o/crc.o/vsnppd.o）+ 2 次链接 + `Package '6b129b068851896169fae42d399fa922d239ce8a' created`，错误扫描 0）
- 上游测试用例通过率：**0/0（不适用）** —— 上游无自动化测试入口，清点证据见上
- 新增测试用例通过率：**10/10（100%）**；检查点 **30/30**（`ALL PASS`）

本地门禁（真机 aarch64 OHOS 原生执行）：

| 门禁 | 结果 |
|------|------|
| `conan create`（全量重建） | ✅ 0 error，`Package '6b129b06…' created` |
| `conan-verify`（G0–G4 + L2/L4/L5） | ✅ Verdict PASS |
| W3 本地 CI 模拟 | ✅ `JC_RESULT=pass`、`L0_RESULT=pass`、`L1_RESULT=pass`（含 L1e 破坏性反向测试）、`L5_RESULT=pass`、`Pass rate 100.0% (1/1)`；`L2=skip`（守护进程无 `--version`）、`L4=warn`（补丁沿用上游 `sprintf`，写入 21 字节 buffer ≤18 字节，无溢出） |
| `finish` 收尾 | ✅ finalize 通过（一致性问题 0 / 缺失项 0）、W5 本包知识完整（`unreferenced=0`）、submit 就绪 |
| PF1–PF8 前置闸（离线按 PR 清单实跑） | ✅ 全部通过 |
| `.ci-result.json` | ✅ `exit_code=0`，`integrity_hash` 与 `log_sha256` 双哈希重算一致，mtime 晚于 `conanfile.py` |

## 补充说明

1. **适配内容（2 个可移植性补丁，不含任何平台宏，Linux/OHOS 通用）**
   - `patches/0001-rtapd.c.patch`
     - `send_tnpp_packet()` 在 `int` 返回值函数里裸 `return;` → clang 15 默认把 `-Wreturn-type` 判为 **error**（改为 `return 0`）
     - `strtoq` 是 glibc/BSD 扩展，**musl 无此符号**：编译期只告警，链接期 `ld.lld: undefined symbol: strtoq` → 改 `strtoll`
     - `sprintf(id, "!%qX", pagenum)` 使用 `%q` 长度修饰符（glibc 的 `%ll` 别名），**musl 的 printf 不支持**：
       实测 `sprintf` 返回 -1 且输出被截断为 `"!"`（**编译/链接全绿，运行期静默丢页面 ID**）→ 改 `"!%llX", (long long)`
   - `patches/0002-vsnppd.c.patch`：`vsnppd.c` 同一处裸 `return` → `return 0`
   - 补丁复验：从官方 tarball 重新解压后按序 `patch -p1`，与适配树 9 个源文件**逐字节一致**（差异 0）
2. **依赖**：无。上游 Makefile 中 mSQL/PostgreSQL/MySQL 的 `CFLAGS`/`LIBS` 全为注释行、`LIBS` 为空，
   默认构建只链接 libc；本包**不**打开 `-DUSE_POSTGRESQL`（避免凭空引入 libpq 依赖）。
3. **PF9 预检误报留痕（本 PR 使用 `--no-preflight` 的依据）**：本地以 `no_preflight=False` 实跑一次，
   `PF1–PF8 全部真实通过`，唯一拦截项是
   `PF9 变更路径缺版本目录层（须 archives/<字母>/<包>/<版本>/<文件>）`，命中的正是**软件级**三件套
   `archives/rtapd/{README.md,manifest.yaml,commands.json}` —— 而归档规范（ARCHIVE-SPEC §6 / R38）
   本就要求 `commands.json` 等放在软件级；仓库 main 上同类软件级文件已有 **13695** 个，
   近期并入的 `sysnews`（`archives/s/sysnews/{README.md,commands.json,manifest.yaml}`）亦为同一形态并通过 CI。
   故判定 PF9 对本 PR 为误报，按 SKILL 提供的逃生口 `--no-preflight` 建 PR，特此留痕。
4. **`finish` 的非阻塞红项（与本包无关）**：(a) G0 `clean-verify` 因 `clean_verify.py` 硬编码 `./configure`，
   纯 Makefile 工程必失败（exit 127）——SKILL 明确该步"平台限制可跳过"，干净重建证据以 G2 + W3 为准；
   (b) `step5b` 图谱全局检查报 `E219/E253/E305` 的 `root_cause` 为空，属**他包知识条目**的历史格式问题，本包未改动。
5. **证据报告（原始日志未随 PR 提交，仓库 12287 个包中仅 2 个提交 `reports/logs/`）**：
   - `reports/test-report.md` — 上游 N=0 清点证据、10 用例 / 30 检查点逐项结果、首轮 CI 失败复现与复现命令
   - `reports/conan-verify-report.md` — G0–G4、L2/L4/L5 门禁结论
   - `reports/pr-body.md` — 本正文
   本地复现：`conan create archives/r/rtapd/1.7 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable`
6. 新增知识草稿：`knowledge/drafts/rtapd-1.7-musl-strtoq-q-format-silent-truncation.kv`
   （musl 移植 glibc/BSD 遗留 C 代码的三层陷阱，带 `prescan_pattern` 可直接派生预扫描规则）。
7. **首轮 CI 失败（PR #15109 构建 #81303）的根因与修复**：失败步骤为 `conan-build-test`，
   首个错误是 `FAIL: rtapd exited during startup` → `Error Operation not permitted (1) at bind unix socket`
   （编译与打包已成功，`Package '6b129b06…' created`）。
   - **根因**：`test.sh` 原先用裸 `mktemp -d` 选沙箱目录，落到了 CI Worker 的 `TMPDIR`（用户数据目录
     `$HOME/.cache/tmp`）。**OHOS 沙箱只允许部分目录创建 unix socket**：本机实测同一路径下
     `/storage/Users/currentUser/.cache` 与 `$HOME` 均 `bind() → errno=1 Operation not permitted`，
     而 `/data/storage/el2/base/temp`、`/data/storage/el2/base/cache`、`/data/storage/el1/base` 均 OK；
     `/tmp` 只读、`/dev/shm` 不可写。（同仓库已合入的 `archives/l/libmilter/8.18.2` 记录过同一现象。）
   - **修复**：`check_rtapd.c` 新增 `--pick-sockdir`，按 `$TMPDIR → $TMP → $TEMP →
     /data/storage/el2/base/temp → /data/storage/el2/base/cache → /data/storage/el1/base → /dev/shm → /tmp`
     顺序用**真实 `bind()`**（`SOCK_DGRAM`，`addrlen = strlen(sun_path) + 2`，与 `rtapd.c` 完全一致）
     探测首个可用目录；`test.sh` 据此建沙箱（新增用例 `consumer.ohos.sandbox_dir`）。
     顺带把存活性判定从裸 `kill -0` 改为 `/proc/<pid>/stat` 优先（可识别僵尸进程，
     同 `archives/b/blockdomains` 先例），启动/退出断言改为可观测日志事实
     （`Entering into main loop` / `Exiting from main loop`）。**未改动任何上游源码或补丁。**
   - **本地复验（对照实验）**：修复后常规环境 `ALL PASS`；`TMPDIR=$HOME/.cache`（拒 bind）下探测回落
     `/data/storage/el2/base/temp` 且 `ALL PASS`；把探测块换回裸 `mktemp -d` 则**逐字复现** CI 失败
     （`FAIL: rtapd 未进入主循环 … Error Operation not permitted (1) at bind unix socket`，rc=1）。
