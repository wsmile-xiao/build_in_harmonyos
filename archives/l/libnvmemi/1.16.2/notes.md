# libnvmemi 1.16.2 — 适配说明

## 这是什么

`libnvme-mi` 是 NVMe 管理接口（NVMe-MI，NVMe Management Interface）的库：
在带外/带内管理通道上，用 **MI Control Primitive**（读 MI 数据结构、读写 MI 配置、
子系统健康轮询）与 **MI Admin 命令**（把 NVMe Admin 命令封装进 MI 报文）管理
NVMe 控制器，传输层是 **MCTP**（AF_MCTP 原始套接字；可选 libdbus 版发现）。

上游 **libnvme 仓库同时产出两个库**：

| 库 | 内容 | 本包 |
|---|---|---|
| `libnvme.so` | A 面：sysfs/ioctl 直通、树模型、JSON/NBFT/Telemetry | ✗ 不交付（见下） |
| `libnvme-mi.so` | MI 协议层 + MCTP 传输 | ✓ 交付 |

v1.16.2 里 **没有独立的 libnvme-mi 仓库**（`linux-nvme/libnvme-mi` 不存在），
MI 库就是 `libnvme` 同一份源码树里的第二个 library 目标。

## 交付内容

```
include/libnvme-mi.h            ← 消费者入口头（#include <libnvme-mi.h>）
include/nvme/{mi,types,tree,log,util,ioctl,fabrics,linux,filters,nbft,api-types}.h
lib/libnvme-mi.so → .so.1 → .so.1.16.2
lib/pkgconfig/libnvme-mi.pc     ← prefix 已重写为 ${pcfiledir}/../..（可重定位）
licenses/COPYING                ← LGPL-2.1-or-later
```

## 关键适配决策

### 1. 为什么本包零 requires

`src/meson.build` 里 `libnvme-mi` 只 `link_with: libccan`（ccan 静态进库）；
可选依赖仅 `libdbus`（`CONFIG_DBUS` 分支：dbus 版 MCTP 发现），本包关闭。
实测：

```
$ nm -D --undefined-only lib/libnvme-mi.so.1.16.2 | grep -c nvme_   # → 0
```

即 **libnvme-mi.so 不引用任何 libnvme.so 符号**，自包含。
json-c / openssl / keyutils / liburing 只服务 `libnvme.so` 的能力 → 全部 disabled，
符合 W0/R36「只启用已发布依赖、不引入无意义传递依赖」。

### 2. 为什么剔除 libnvme.so

本包名是 `libnvmemi`，交付物应当只有 MI 库。同一份 meson 工程会顺带装上
`libnvme.so`/`libnvme.h`/`libnvme.pc`，`package()` 里把它们删除（test_layout.py
第 [2] 组专门守着这条）。消费者头 `nvme/mi.h` 需要 `nvme/tree.h`、`nvme/ioctl.h`
等，所以 `include/nvme/*.h` 全量保留（这是 MI 头的包含闭包）。

### 3. OHOS 侧补丁：仅 1 个（测试辅助工具的临时文件）

`patches/0001-ohos-tmpdir-aware-test-tmpfile.patch` —— 只改上游
`test/utils.c`（测试辅助工具，**不进 package 产物**）：

* 上游 `test_setup_log()` 用 libc `tmpfile()` 建日志缓冲，musl 的 `tmpfile()`
  **硬编码 `/tmp`**（`P_tmpdir`），而 OHOS 的 `/tmp` 是只读挂载
  （`ci/conan/build_and_test.sh` 亦注明 "OHOS /tmp is read-only"），
  因此失败 → `err(EXIT_FAILURE, ...)` → **退出码 1**。
* CI #65437 实证：只有 `test/mi` 与 `test/mi-mctp` 这两个用例（全仓**仅此二者**
  使用 `test/utils.c`）失败，且是 `exit status 1`（不是断言 abort 的 134）。
* 补丁新增 `test_tmpfile()`：按 `$TMPDIR` → `$TMP` → `$TEMP` → `$HOME`
  依次试 `mkstemp`（**只认真正成功的那一个**，`/tmp` 这类不可写的候选会被跳过），
  成功后立即 `unlink`（保持 `tmpfile()` 的匿名语义、不留垃圾文件），
  四个变量都不可用时才回退 libc `tmpfile()`；`test_setup_log()` 改调它。
  （真机实测：OHOS `tmpfile()` 即使 `$TMPDIR` 指向可写目录也返回 NULL/EACCES ——
  它是**完全无视** `$TMPDIR` 的，所以不能靠"给 TMPDIR 就完事"，必须自己找可写目录。）
  该改动在所有平台都安全，与仓库内 `enscript/1.6.6` 的
  `0003-ohos-tmpdir-aware-tmpfile.patch` 同款做法。
* 库本体（`src/`）无需补丁：缺少 `<linux/mctp.h>` 时上游自动用仓库内 `src/nvme/mi-mctp-compat.h`，
  并 `#if !defined(AF_MCTP) #define AF_MCTP 45`（`src/nvme/mi-mctp.c:42`）。
* 无 Python/pip：`-Dpython=disabled`；无需文档：`-Ddocs=false`。
* meson 在 CI worker 上探测归档器用裸名（`llvm-ar` 等）而 worker 把这些变量
  导出为裸名且不在 PATH → `generate()` 先弹出 `AR/AS/STRIP/NM/RANLIB` 再让 meson
  重新探测（仓库内 erfa 2.0.1 同款处理，9 个配方共用）。
* `.pc` 里 meson 以 `--prefix=/` 安装（conan DESTDIR 打包），`prefix` 会写成 `/`
  → `package()` 重写为 `${pcfiledir}/../..`。

## 测试证据（平台 rule12）

### ① 上游官方测试：build() 内真跑 `meson test`

CI 的 host/build profile 同为 `ohos-aarch64`（原生），因此用例真跑。
本机原生复现（同一份源码 + 配方同款 meson 选项）：

```
Ok:                29
Expected Fail:      2
Fail:              0
```

31 个用例全部执行，其中 MI 专属两条：

| 用例 | 源文件 | 说明 |
|---|---|---|
| `libnvme:mi` | `test/mi.c`（282 条断言） | 自定义 transport 注入：控制器列表扫描、MI Read MI Data、Admin Identify、MI/NVMe 双路错误、MPR 重试、AEM |
| `libnvme:mi-mctp` | `test/mi-mctp.c`（96 条断言） | 伪造 MCTP 对端拦截 `sendmsg/recvmsg/poll`：tag 分配、MPR/MPRT 超时钳制、AEM 同步 |

失败即 `build()` 抛异常（硬门禁），成功时输出 `HMBS_UPSTREAM_TEST_RESULT ...`。

#### OHOS shebang 适配（CI #65377 实测，不改上游源码）

上游 meson 把 `test()` 的 exe 直接 `execve`，而其中若干"用例本体"是脚本：

| 用例 | 被测脚本 | shebang | OHOS 结果 |
|---|---|---|---|
| `tree-pcie` / `tree-apple-nvme` | `test/sysfs/tree-diff.sh` | `#!/bin/bash -e` | bash 只在 `/data/service/hnp/bin/` → 内核解析 shebang 失败 |
| `config-pcie` / `config-pcie-with-tcp-config` / `hostnqn-order` / `psk-json-*` | `test/config/config-diff.sh` | `#!/bin/bash -e`（且用 bash 数组与 `[[ ]]`，**不能**改成 `/bin/sh`） | 同上 |
| `kdoc`（文档 lint） | `scripts/kernel-doc-check` | `#!/bin/bash`，内部再调 perl 的 `scripts/kernel-doc` | OHOS 既无 `/bin/bash` 也无 `perl` |

`execve` 返回 ENOENT 时 **meson 不会把它记成"该用例失败"，而是抛
`Unhandled python OSError` 并中断整轮测试**（CI #65377 表现为
`Ok 13 / Fail 2` 后直接 abort，计数不完整）。

处理方式：`build()` 现场生成一个 `--wrapper`（meson 各版本都有的开关），
把这两类 helper 脚本转交给真实 bash（`/data/service/hnp/bin/bash` → `/usr/bin/bash`
→ PATH 上的 `bash`）并补回 shebang 里的 `-e`；其余用例（编译型 ELF）原样 `exec`。
唯一无法运行的是文档 lint `kdoc`（还需 perl），按 GNU 约定 `exit 77` 让 meson 记为
**SKIP**（不是通过、也不是失败），并在 `HMBS_UPSTREAM_TEST_RESULT` 的 `skipped`
字段里显式打印。

#### OHOS 临时文件适配（CI #65437 实测 → 补丁 0001）

wrapper 生效后 OHOS 上 31 个用例全部注册并执行（`kdoc` 记 SKIP），
但 `libnvme:mi`、`libnvme:mi-mctp` 仍报 `exit status 1`：

```
13/31 libnvme:mi        FAIL   exit status 1
14/31 libnvme:mi-mctp   FAIL   exit status 1
Ok: 26   Expected Fail: 2   Fail: 2   Skipped: 1
```

二者是全仓**仅有的**使用 `test/utils.c` 的用例，其 `test_setup_log()` 调
libc `tmpfile()` → musl 硬编码只读的 `/tmp` → `err(EXIT_FAILURE)` 退出码 1
（断言失败会是 `killed by signal 6`/134，排除断言因素）。
修法见「关键适配决策 §3」，即补丁 0001（只动测试辅助工具）。

### ② 完整消费者用例（端到端业务流程）

`test_package/test_libnvme_mi.c`：**只**链接交付的 `libnvme-mi.so` + 公共头。
鸿蒙 PC 上没有 MCTP 控制器，因此用例在进程内用 **ELF 符号介入**造一个假 MCTP 设备：

```
socket(AF_MCTP, SOCK_DGRAM, 0)  ──介入──▶  返回 AF_UNIX SOCK_DGRAM socketpair 的一端
sendmsg(fd, MI 请求)            ──介入──▶  解析请求 → 生成 MI 响应 → 从设备侧注入 socketpair
poll()/recvmsg()                           不介入：库直接从内核缓冲区读到响应（真实收发路径）
```

（库内部 `nvme/mi-mctp.c` 的 ops 表调用的就是 libc 的 `socket`/`sendmsg`；可执行文件
用 `ENABLE_EXPORTS`/`--export-dynamic` 把自身符号放进动态符号表，即可对共享库生效。
不用 LD_PRELOAD，也不用被版本脚本隐藏的 `__nvme_mi_mctp_set_ops`。）

业务链路与核对结果（32 项，逐项显式比对，无断言宏）：

1. `nvme_mi_create_root` + `nvme_mi_open_mctp(net=1, eid=8)` → 端点建立、默认超时 5000 ms；
2. `nvme_mi_scan_ep`（MI Control Primitive，读控制器列表）→ 枚举出设备侧宣布的 3 个控制器 id = 1/4/5；
3. 逐个 `nvme_mi_admin_identify_ctrl`（MI Admin Identify，CNS=1）→ **SN/MN/FR/VID/SSVID/RAB/CNTLID 与设备侧注入数据逐字段一致**；
4. 错误路径：不支持的 MI 数据结构 → `rc == NVME_MI_RESP_INVALID_CMD_SIZE`(=5)；不支持的 Admin 命令（Get Features）→ `nvme_status_get_value(rc) == 0x4006`（设备侧在 cdw3 里回的 SF 值），且设备侧计数器确认两种请求都真实到达。

实测输出（本机 gcc 复现，OHOS 由平台 CI 真跑）：

```
设备侧计数：MI=2 Admin=4 Identify=3 不支持=2
消费者用例结果：32 项检查，0 项失败
```

### ③ 适配自检（M = 21 条，非上游用例）

`test_package/test_layout.py`：MI 库与 soname 链、未误带 `libnvme.so`/`libnvme.h`、
公共头包含闭包、pkg-config 契约可重定位、LGPL COPYING、无上游测试程序与构建中间产物、
无隐藏文件（JC5）。实测 21/21 通过；`pkg-config --cflags --libs libnvme-mi`
在任意安装前缀下都指向包内的 include/lib。

## 版本与来源

* 上游 tag：`v1.16.2`（`https://github.com/linux-nvme/libnvme`）
* tarball：`https://github.com/linux-nvme/libnvme/archive/refs/tags/v1.16.2.tar.gz`
* sha256：`1d850d5a871559abf641d6e6b63bb86047e4cb26f3ad144597c2c64b3cff7231`
* 下载双校验：sha256 一致 + `tar tzf | wc -l` = 1325（与 codeload 同源 URL 结果一致）
* 许可：LGPL-2.1-or-later（`COPYING` 随包交付）
