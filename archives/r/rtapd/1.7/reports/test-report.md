# rtapd 1.7 测试报告（上游测试 + 鸿蒙消费者用例）

- 软件/版本：`rtapd/1.7`
- 目标平台：OpenHarmony / HarmonyOS PC aarch64（`aarch64-linux-ohos`，musl）
- Profile：`ci/conan/profiles/ohos-aarch64`（clang 15，os=OHOS，arch=armv8，Release）
- 执行环境：真实 aarch64 OHOS 主机（**原生执行**，非 qemu 仿真）
- 执行时间：2026-10-08 22:03–22:05 首次全量重建；**22:21 清空本地 conan 缓存后再次全量重建**
  （`conan remove rtapd/1.7@ohpcd/stable -c` → 真实 `Building from source` + 4 个编译单元 + `Package '…' created`），
  消费者用例两次均为 `ALL PASS`；`reports/conan-create.log` 保留的是最后一次全量重建的完整日志
- **2026-10-10 修复首轮 CI 失败后再次复验**（详见第五节）：常规环境与「CI 同条件」下均
  `10 项用例 / 30 个检查点 ALL PASS`

---

## 一、上游自带测试：N = 0，N′ = 0，跳过 0

| 项目 | 值 |
|------|-----|
| 上游测试命令 | 无（Makefile 无 `check`/`test` 目标） |
| 用例总数 N | 0 |
| 实际执行 N′ | 0 |
| 通过 / 失败 / 跳过 | 0 / 0 / 0 |

**清点证据（逐项可复核）**

| # | 证据 | 命令 | 原始输出要点 |
|---|------|------|--------------|
| 1 | Makefile 全部目标 | `grep -n "^[a-z-]*:" Makefile` | `default:` `rtapd:` `vsnppd:` `clean:` `install.config:` `install:` —— 无 `check`、无 `test` |
| 2 | 源码包无测试目录/文件 | `tar tzf rtapd-1.7.tar.gz`（21 项）`; ls \| grep -i "test\|check"` | 无 `tests/`，无 `*test*`/`*check*` 源文件（仅有 `tap_dev.conf`/`tap_route.conf` 等示例配置） |
| 3 | 第三方独立佐证 | Alpine aports `main/rtapd/APKBUILD` | `options="!check"` —— 显式跳过 check 阶段 |
| 4 | 唯一自检入口 | `rtapd`/`vsnppd` 自带 `usage()` | 非法参数打印用法并 `exit(1)`（见消费者用例第 1、3 项） |

**结论**：上游**没有自动化测试入口**，无法给出"N/N′/通过率"以外的统计；`test_package` 的消费者用例是
本包唯一的功能验证来源，**不用于替代上游统计**（上游统计如上，明确为 0）。

---

## 二、鸿蒙消费者用例（`test_package/`，必须新增的平台用例）

**执行命令**（由 `test_package/conanfile.py` 的 `test()` 触发，`conan create` 内自动运行）：

```bash
'/data/service/hnp/bin/bash' \
  '<test_package>/test.sh' '<build>/check_rtapd' '<pkg>/bin'
```

`check_rtapd` 由 `test_package` 的 `build()` 用 OHOS 工具链编译（`/data/service/hnp/bin/clang -O2 -Wall`），
是一个**真实消费者客户端**：扮演 `rtnppd` 按 rtapd 自身的 TNPP 线上格式（含 CRC-16/ARC 校验）向
守护进程的 `ExtSocketIn` AF_UNIX 数据报 socket 投递 CAP 页面。

### 用例清单（10 项，全部实跑；检查点 30 个）

| # | 用例名 | 断言内容 | 结果 |
|---|--------|----------|------|
| 0 | `consumer.ohos.sandbox_dir` | 用真实 `bind()`（与 rtapd 同 socket 类型/addrlen）在候选目录中探测出允许 AF_UNIX 的沙箱目录；修复点见第五节 | ✅ PASS |
| 1 | `consumer.ohos.rtapd_usage_exit_code` | `rtapd -x 9` 打印含 `rtapd v1.7` / `Usage: rtapd [-ds]` 的用法，退出码 = 1 | ✅ PASS |
| 2 | `consumer.ohos.rtapd_missing_config_exit2` | `rtapd -d -s -C <不存在>` 退出码 = 2（配置错误路径） | ✅ PASS |
| 3 | `consumer.ohos.vsnppd_usage_exit_code` | `vsnppd -Q` 打印 `vsnppd v1.1` 用法，退出码 = 1（第二个二进制可运行） | ✅ PASS |
| 4 | `consumer.ohos.daemon_boot_foreground` | `-d -s -x 4 -C <沙箱配置> -p <转储>` 前台启动，日志出现 `Entering into main loop`，且进程未在进入主循环后退出 | ✅ PASS |
| 5 | `consumer.ohos.daemon_bind_unix_socket` | `ExtSocketIn` 被创建为 unix socket（`-S` 判定）；pid 文件存在、内容为合法数字、且指向一个真实存活进程 | ✅ PASS |
| 6 | `consumer.ohos.config_parse_dump_override` | `-p` 转储含 `TNPPAddress 0001`、`ExtSocketIn`/`ExtSocketOut`、`LockDir`、`DeviceFile`、`RoutingTable`、`Device` 全部沙箱覆盖值 | ✅ PASS |
| 7 | `consumer.ohos.tnpp_cap_page_end_to_end` | 客户端投递 CAP 页面 → 日志 `routed to device 'FILE01'`、`saved in file '<沙箱>/dev01.pgs'`；设备文件内出现页面正文 `HELLO-OHOS-RTAPD` | ✅ PASS |
| 8 | `consumer.ohos.cap_page_id_hex_format` | 日志出现 `CAP page packet to '!1234ABCD' (func 31) from 0042`，且**不得**出现被截断的 `'!'` | ✅ PASS |
| 9 | `consumer.ohos.sigterm_graceful_exit` | 收到 SIGTERM 后日志出现 `SIGTERM or SIGINT has received` 与 `Exiting from main loop`，且进程确实消失 | ✅ PASS |

**原始结果行**（`test.sh` 输出，节选自 `reports/conan-create.log`）：

```
[consumer.ohos.sandbox_dir] AF_UNIX bind 可用目录 = /data/storage/el2/base/cache
[consumer.ohos.rtapd_usage_exit_code] rtapd -x 9 -> usage + exit 1
[consumer.ohos.rtapd_missing_config_exit2] rtapd -C <missing> -> exit 2
[consumer.ohos.vsnppd_usage_exit_code] vsnppd -Q -> usage + exit 1
[consumer.ohos.daemon_boot_foreground] rtapd -d -s -x 4 -p <dump>
[consumer.ohos.daemon_bind_unix_socket] ExtSocketIn 已创建为 unix socket
[consumer.ohos.config_parse_dump_override] -p 转储反映沙箱覆盖项
[consumer.ohos.tnpp_cap_page_end_to_end] 消费者客户端投递 TNPP CAP 页面
[consumer.ohos.cap_page_id_hex_format] CAP 页面 ID 十六进制格式正确
[consumer.ohos.sigterm_graceful_exit] SIGTERM 被处理并退出
ALL PASS
```

**关键断言为何是本包的平台核心证据**

用例 8 走的就是本次补丁修改的那段代码（`rtapd.c` CAP 块处理：`strtoll` + `"!%llX", (long long)`）。
OHOS 使用 musl，而 musl 的 `printf` 不支持 `%q` 长度修饰符——在未修复的源码上，
`sprintf(id, "!%qX", pagenum)` 返回 -1 且 `id` 只剩 `"!"`（**编译无任何告警**）。因此该用例把
"静默丢数据"变成了硬失败；用例 0/4/5/6/7 同时证明 OHOS 上 AF_UNIX socket（含目录策略）、
配置文件解析、路由与文件设备落盘这条真实链路可用。

---

## 三、日志与复现方式

| 内容 | 路径 |
|------|------|
| `conan create` 全量日志（含上游编译输出、消费者用例逐行输出、`ALL PASS`） | `reports/conan-create.log` |
| 配方门禁报告（G0–G4、L2/L4/L5） | `reports/conan-verify-report.md` |

> **日志留存说明**：`reports/conan-create.log` 属本地产物，未随 PR 提交（`.gitignore:96` 忽略 `reports/`）。
> 本地复现命令：
> `conan create archives/r/rtapd/1.7 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable`
> 该命令会在 `Testing the package` 阶段自动编译并运行 `test_package/check_rtapd.c` 与 `test_package/test.sh`。

---

## 四、首轮 CI 失败诊断与修复（2026-10-10）

**现象**（PR #15109，构建 #81303，`conan-build-test` 步骤）：

```
o[consumer.ohos.daemon_boot_foreground] rtapd -d -s -x 4 -p <dump>
oFAIL: rtapd exited during startup
oOct 10 20:30:33 Main config: 7 lines
oOct 10 20:30:33 Error Operation not permitted (1) at bind unix socket
```

编译与打包本身成功（`Package '6b129b06…' created`），失败点在 `test_package` 启动守护进程。

**根因**：`test.sh` 原先用裸 `mktemp -d` 选沙箱目录，落到 CI Worker 的 `TMPDIR`（用户数据目录，
`$HOME/.cache/tmp`）。OHOS 沙箱**只允许部分目录创建 unix socket**：本机实测同一代码路径

| 目录 | `bind()` 结果 |
|------|---------------|
| `/storage/Users/currentUser/.cache`（CI `TMPDIR` 同类） | ❌ `errno=1 Operation not permitted` |
| `/storage/Users/currentUser`（`$HOME`） | ❌ `errno=1 Operation not permitted` |
| `/data/storage/el2/base/temp` | ✅ OK |
| `/data/storage/el2/base/cache` | ✅ OK |
| `/data/storage/el1/base` | ✅ OK |
| `/dev/shm` | ❌ `mkdtemp: Permission denied` |
| `/tmp` | ❌ `Read-only file system` |

（同仓库已合入的 `archives/l/libmilter/8.18.2` 在 `test_milter.c` 中记录过同一现象并采用同样的探测法。）

**修复**：

1. `check_rtapd.c` 新增 `--pick-sockdir`：按 `$TMPDIR → $TMP → $TEMP → /data/storage/el2/base/temp →
   /data/storage/el2/base/cache → /data/storage/el1/base → /dev/shm → /tmp` 顺序，用**真实 `bind()`**
   （`SOCK_DGRAM`，`addrlen = strlen(sun_path) + 2`，与 `rtapd.c` 完全一致）逐个探测，返回首个可用目录；
   全部不可用时以 rc=3 退出。`test.sh` 据此建沙箱（`mktemp -d "$BASE/rtapd-test.XXXXXX"`）。
2. 顺带加固存活性判定：`alive()` 以 `/proc/<pid>/stat` 分类（可识别僵尸进程、不依赖信号权限，
   同 `archives/b/blockdomains` 先例），`kill -0` 仅作 `/proc` 不可用时的回退；
   启动断言改为可观测事实（日志 `Entering into main loop`），退出断言补上 `Exiting from main loop`。

**复验（对照实验）**：

| 场景 | 脚本版本 | `TMPDIR` | 结果 |
|------|----------|----------|------|
| A 常规 | 修复后 | `/data/storage/el2/base/cache` | `ALL PASS`（rc=0） |
| B CI 同条件 | 修复后 | `$HOME/.cache`（拒 bind） | 探测回落 `/data/storage/el2/base/temp` → `ALL PASS`（rc=0） |
| C 修复前对照 | 裸 `mktemp -d` | `$HOME/.cache`（拒 bind） | ❌ **逐字复现 CI 失败**：`FAIL: rtapd 未进入主循环 (sandbox=…/.cache/tmp…, socket=…/queue.out)` + `Error Operation not permitted (1) at bind unix socket`，rc=1 |
| D 平台全禁 | 修复后 | 全部候选不可用 | 打印 SKIP 诊断并 exit 0（平台限制，非本包缺陷） |

---

## 五、结论

- 上游测试：**N=0 / N′=0 / 跳过 0**（无测试入口，证据见第一节）
- 鸿蒙消费者用例：**10 项用例 / 30 个检查点，全部 PASS**，且是真实 aarch64 OHOS 主机上的原生执行
- 该包**新增了至少一个鸿蒙平台消费者用例**（用例 0/4/5/6/7 为平台机制断言；用例 8 直接验证本次补丁的正确性）
- 首轮 CI 失败已在本地**逐字复现**并修复，修复后「CI 同条件」下全绿（见第四节）
