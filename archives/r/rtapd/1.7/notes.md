# rtapd 1.7 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure）
- 编译日期: 2026-10-08
- 编译器: OHOS NDK clang 15.0.4（aarch64-linux-ohos，musl）
- 状态: built
- 语言预检: `lang-preflight` → `detected=c`（21 个文件，主体为 C；`build_system` 探测为 autotools 是误判——源码包只有 Makefile，配方按 makefile 手写），与任务语言 cpp 同属 C/C++ 兼容族，预检放行
- 源码: `rtapd-1.7.tar.gz`（sourceforge 项目 rtnppd 官方发布，顶层目录 `rtapd/`），
  sha256 `cb10617032d7e3da23b3e7fe153aeb1751ac6a559fc43725b9ba5fe91296ddd7`，
  sha512 与 Alpine aports 登记的 `a4759b5a…78f63` 逐字节一致（同一份上游归档）
- 依赖: 无。上游 Makefile 中 mSQL/PostgreSQL/MySQL 三组 `CFLAGS`/`LIBS` 全是注释行，活动配置只有
  `CFLAGS += -O2 -pipe -g` 与空的 `LIBS`，默认构建仅链接 libc

## 编译步骤

1. `make -j1 CC='<ohos clang>' CFLAGS='-O2 -pipe -g'`（CC 取自 conan
   `tools.build:compiler_executables`，不使用任何 shell 环境变量）直接产出 `rtapd` 与 `vsnppd`。
2. 上游 `make install` 需要 root（`mkdir -p /var/spool/psheduler`、`install -o bin -g bin`），
   配方在 `package()` 中直接把两个可执行文件复制到 `bin/`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `rtapd.c:350` / `vsnppd.c:67` 编译直接报错 `non-void function 'send_tnpp_packet' should return a value [-Wreturn-type]` | 上游 2001 年代码在 `int` 返回值函数里写裸 `return;`；clang 15 默认将 `-Wreturn-type` 视为 error（GCC 14 起同样） | 补丁 0001/0002 改为 `return 0`（该分支是「包长超限」失败路径，返回 0 与调用方语义一致） |
| 2 | 链接期 `ld.lld: error: undefined symbol: strtoq` | `strtoq` 是 glibc/BSD 扩展，musl 未提供；编译期只报 `implicit-function-declaration` 告警，不拦 | 补丁 0001 改为标准 `strtoll`（返回 `long long`，与 `quad_t` 一致） |
| 3 | 即使修好 strtoq，CAP 页面 ID 仍会退化为 `"!"`（静默数据损坏，编译不报错） | `sprintf(id, "!%qX", pagenum)` 使用 `%q` 长度修饰符（glibc 的 `%ll` 别名），musl printf 不支持；实测 `sprintf` 返回 -1 且 `id` 只剩 `"!"` | 补丁 0001 改为 `sprintf(id, "!%llX", (long long) pagenum)`（OHOS `sys/types.h` 中 `quad_t` 即 `long long`） |

**问题 3 的实测证据**（OHOS musl 上直接跑的最小复现，与 test_package 的端到端断言同源）：

```c
unsigned long long v = 0x1234ABCDULL; char a[64], b[64];
sprintf(a, "!%qX",  v);   /* q-ret=-1   q-out=[!]        */
sprintf(b, "!%llX", v);   /* ll-ret=9   ll-out=[!1234ABCD] */
```

适配后 test_package 日志中 `CAP page packet to '!1234ABCD' (func 31) from 0042` 即为该修复的正向验证。

## 源码修改

- `patches/0001-rtapd.c.patch`：`send_tnpp_packet()` 裸 `return` → `return 0`；两处 CAP 块处理改
  `strtoq`→`strtoll`、`"!%qX"`→`"!%llX", (long long)`（portability，非平台专属，Linux/OHOS 通用）。
- `patches/0002-vsnppd.c.patch`：`vsnppd.c` 同一处裸 `return` → `return 0`（portability）。
- 两个补丁的新增行均不含任何平台宏（无 `__OHOS__` 之类守卫），未使用 `replace()` 注入。

## 上游测试清点（R51）

上游**没有任何自动化测试入口**，清点证据：

- `Makefile` 的全部目标：`default` / `rtapd` / `vsnppd` / `clean` / `install.config` / `install` —— 无 `check`、无 `test`
- 源码包（`tar tzf` 全量 21 个条目）内无 `tests/`、无 `*test*`/`*check*` 源文件
- 第三方独立佐证：Alpine aports 的 `rtapd` APKBUILD 显式声明 `options="!check"`（跳过 check 阶段）
- 唯一的自检入口是两个程序自带的 `usage()`（非法参数时打印用法并 `exit(1)`）

结论：上游用例总数 **N = 0**，可运行 **N′ = 0**，无跳过项。功能验证改由 `test_package/` 的
鸿蒙消费者用例承担，且该用例**必须**至少覆盖一条真实的平台链路（见下），不以「编译通过」代替可用性。

## 验证结果

- `conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`：
  源码全量重建成功，`Package '<id>' created`（详见 `reports/conan-create.log`）。
- 上游测试：N=0 / N′=0 / 跳过 0（无测试入口，证据见上）。
- 消费者用例（`test_package/test.sh`，30 个检查点，`ALL PASS`）在真实 aarch64 OHOS 主机上实跑，覆盖：
  0. 沙箱目录选择：用真实 `bind()`（与 rtapd 同 socket 类型/addrlen）在候选目录中探测出允许
     AF_UNIX 的目录（`[consumer.ohos.sandbox_dir]`）；这是首轮 CI 失败的修复点，见「对话 #2」
  1. `rtapd -x 9` → usage + exit 1（ELF 加载/运行、getopt/printf/退出码）
  2. `rtapd -d -s -C <missing>` → exit 2（配置错误路径）
  3. `vsnppd -Q` → usage + exit 1（第二个二进制可运行）
  4. 沙箱内前台启动 → 日志出现 `Entering into main loop`、`ExtSocketIn` 被创建为 AF_UNIX
     SOCK_DGRAM socket、pid 文件写入且其中的 PID 指向一个真实存活进程
  5. `-p` 配置转储反映全部沙箱覆盖项（TNPPAddress/ExtSocketIn/ExtSocketOut/LockDir/DeviceFile/RoutingTable/Device）
  6. 消费者 C 客户端（扮演 rtnppd，按 rtapd 自身 TNPP 线上格式 + CRC-16/ARC 发包）投递 CAP 页面后，
     守护进程日志出现 `CAP page packet to '!1234ABCD' (func 31) from 0042`（**直接验证 `%llX` 修复**）、
     `routed to device 'FILE01'`，且页面正文真实落盘到设备文件
  7. `SIGTERM` 被捕获（日志 `SIGTERM or SIGINT has received` + `Exiting from main loop`）且进程退出

## 交付物

| 文件 | 说明 |
|------|------|
| bin/rtapd | TAP/TNPP 寻呼守护进程 |
| bin/vsnppd | SNPP/TNPP 网关（同源码包构建） |
| licenses/COPYRIGHT | 上游 BSD-2-Clause 许可正文 |

## 注意事项

- 上游仍会随包附带 `email.filter.rtapd`/`fax.filter.rtapd`/`psheduler.pl`/`pfilter.pl` 等
  Perl/Shell 辅助脚本与示例配置；上游 `make install` 才安装它们（且需 root），本配方**未**纳入
  交付物（避免把 Perl 脚本当成二进制命令声明），也未启动这些过滤程序。
- SQL 后端保持上游默认关闭；若下游需要 PostgreSQL/MySQL 路由表，需另开版本并显式加
  `-DUSE_POSTGRESQL` 与 `libpq` 依赖。
- 运行期默认路径（`/usr/local/etc/rtnppd/rtapd.conf`、`/var/run/rtapd.pid`、`/var/spool/lock`）
  均可由配置文件覆盖；`test_package/test.sh` 正是靠全部覆盖到临时目录才无需 root 与串口硬件。

### 对话 #1 [2026-10-08]

- 问题: 首次适配 rtapd 1.7，纯 Makefile 老代码（2001），需要判断它在 OHOS/musl 上到底能不能过，而不是只让编译通过
- 操作: 先用系统 clang 朴素编译枚举真实错误（1 个 error + 61 warnings）→ 逐个定性根因（`-Wreturn-type` 是 error 级；
  `strtoq` 编译期仅告警但链接期必然 undefined symbol；`%q` 编译完全无感但运行期静默截断）→ 用 OHOS musl 上直接跑的最小
  C 程序证明 `%q` 返回 -1、输出退化为 `"!"` → 写成 2 个 portability 补丁（`refresh-patch --auto` 生成）→
  真实 `conan create` 全量重建 → 在真机 aarch64 OHOS 上跑端到端消费者用例
- 结果: 编译 0 error、两个二进制产出；消费者用例 27 条断言 ALL PASS，其中第 6 条从守护进程日志与落盘文件两侧
  同时证明 `%llX` 修复在 musl 上生效（修复前该路径会静默丢掉页面 ID）

### 对话 #2 [2026-10-10]

- 问题: PR #15109 首轮 CI（构建 #81303）在 `conan-build-test` 步骤失败，`[fail] rtapd/1.7 — conan create failed`；
  日志首错为 `FAIL: rtapd exited during startup` → `Error Operation not permitted (1) at bind unix socket`。
  编译与打包均已成功（`Package '6b129b06…' created`），失败在 `test_package` 的守护进程启动。
- 定位: 与本机复现逐字一致 —— `test.sh` 原先用裸 `mktemp -d` 选沙箱，CI Worker 的 `TMPDIR` 是**用户数据目录**
  （`$HOME/.cache/tmp`）；实测该目录可写但 `bind()` 返回 `EPERM`：
  `/storage/Users/currentUser/.cache` → `bind => FAIL (errno=1 Operation not permitted)`；
  而 `/data/storage/el2/base/temp`、`/data/storage/el2/base/cache`、`/data/storage/el1/base` → `bind => OK`。
  即 OHOS 沙箱只允许部分目录创建 unix socket（同仓库已合入的 `archives/l/libmilter` 记录过同一现象）。
- 修复: `check_rtapd.c` 新增 `--pick-sockdir`：按 `$TMPDIR/$TMP/$TEMP → /data/storage/el2/base/temp →
  /data/storage/el2/base/cache → /data/storage/el1/base → /dev/shm → /tmp` 顺序，用**真实 bind()**
  （`SOCK_DGRAM`，addrlen=`strlen(sun_path)+2`，与 rtapd 完全一致）逐个探测，返回首个可用目录；
  `test.sh` 据此建沙箱。顺带把存活性判定由裸 `kill -0` 改为 `/proc/<pid>/stat` 优先（僵尸可辨、不依赖信号权限，
  同 `blockdomains` 先例），并把启动/退出断言改为可观测的日志事实（`Entering into main loop` /
  `Exiting from main loop`）。
- 复验: 对照实验 —— 把探测块换回裸 `mktemp -d`，在 `TMPDIR=$HOME/.cache` 下**逐字复现** CI 失败
  （`FAIL: rtapd 未进入主循环 ... Error Operation not permitted (1) at bind unix socket`，rc=1）；
  修复后同条件下探测回落 `/data/storage/el2/base/temp`，10 个用例 / 30 个检查点 `ALL PASS`；
  常规环境同样 `ALL PASS`。
- 状态: built
---

**编译结束**: 2026-10-10 21:05
**最终状态**: built
