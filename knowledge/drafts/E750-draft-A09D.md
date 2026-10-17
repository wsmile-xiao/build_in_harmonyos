# E750 — OHOS 未随附 iproute2 的 `ip`（toybox 未编 ip applet）：上游测试脚本 `command -v ip || exit 1` 直接退出

- **草稿 ID**: E750-draft-A09D
- **来源库**: miniupnpd 2.3.10（HarmonyOS PC aarch64，clang 15.0.4 / OHOS SDK 26.0.0.18，HongMeng Kernel 1.12.0）
- **状态**: 草稿（待主编 promote 为正式 E 条目）

## 错误特征

上游 `miniupnpd-2.3.10/testgetifaddr.sh` 的第一件事是探测 iproute2：

```sh
# linux 分支
IP="`command -v ip`" || exit 1
EXTIF="`LC_ALL=C $IP -4 route | grep 'default' | sed ...`" || exit 1
```

设备上 `ip` 不存在 → `command -v ip` 返回空、`||` 取 rc=1 → 脚本**一行没跑就 exit 1**，
`make check` 的 `validategetifaddr` 目标随即失败。日志形态：

```text
/bin/sh .../testgetifaddr.sh
IP=ip: not found          # 或 ip: command not found（取决于外壳）
make: *** [check.mk:11: validategetifaddr] Error 1
```

反差在于：测试程序本身（`./testgetifaddr wlan0`）完全可运行并能通过——
失败纯粹来自**工具探测**，不是被测代码问题。

## 触发条件

- 构建系统: 手写 configure + GNU Makefile（任何 `make check` 驱动 shell 测试的项目）
- 阶段: testing（测试脚本前置工具探测）
- 关键字: `command -v ip`、`ip -4 route`、`ip -4 addr show`、`default route`、`testgetifaddr.sh`

## 根因分析

鸿蒙 PC 的 `/bin/toybox` 编入的 applet 集里**没有 `ip`**（实测
`/bin/toybox --list | grep -x ip` 无输出，`busybox --list` 里 `ifconfig`/`route` 有、
`/bin/ip` 不存在），PATH 内也没有 iproute2。而上游测试脚本普遍把
`command -v <tool> || exit 1` 当作硬前置，于是**用例计数里它既不是 PASS 也不是
FAIL，而是"根本没执行"**——若照抄结果填表，极易被误记成测试失败或漏统计。

同一台设备上 `/data/service/hnp/bin/busybox` 自带完整 `ip` applet：

```text
$ busybox ip -4 route
192.168.3.0/24 dev wlan0 scope link  src 192.168.3.16
$ busybox ip -4 addr show wlan0
9: wlan0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 ...
    inet 192.168.3.16/24 brd 192.168.3.255 scope global wlan0
```

## 解决方案

### 推荐方案（不改上游脚本，只补工具）

```sh
B="$PWD/.tools"; mkdir -p "$B"
command -v ip >/dev/null || ln -sf "$(command -v busybox) "$B/ip"
export PATH="$B:$PATH"
make check        # validategetifaddr -> testgetifaddr test OK
```

配方侧（Conan）做法：`build()` 里 `shutil.which("ip")` 缺失且 `shutil.which("busybox")`
存在时，在 build 目录下建 `ip → busybox` 链接并把该目录前置进 `os.environ["PATH"]`，
随后所有 `self.run()`/`make` 子进程都继承。测试语义、脚本内容、断言完全不变。

### 禁止做法

- ❌ `sed -i` 修改上游脚本把 `|| exit 1` 改成 `|| true`，或把 `ip` 换成自造占位脚本
  —— 把"工具缺失"变成"静默通过"，破坏上游用例的可比性，评审按假 PASS 处理。
- ❌ 脚本提前退出时直接记 PASS 或不写归因
  —— 违反 R51 三步法与四分项统计（PASS/FAIL/SKIP/NOT_RUN 必须闭合到 N）。

## 验证

```sh
# 复现（全部落在任务私有目录，/tmp 只读不可用；构建目录必须含 ./testgetifaddr）
T=/storage/Users/currentUser/tmp/miniupnpd-2.3.10
S=$T/w0/src/miniupnpd-2.3.10 ; B=$T/w0/trial/b2 ; P=$T/w0/bin

# ① 症状：PATH 无 ip 时脚本无输出、静默 rc=1
( cd "$B" && PATH=/data/service/hnp/bin:/usr/bin:/bin sh "$S/testgetifaddr.sh" )
echo "rc=$?"        # -> 1，且 stdout 为空

# ② 修复：busybox 的 ip applet 挂到任务本地 bin 并前置 PATH
mkdir -p "$P" && ln -sf /data/service/hnp/bin/busybox "$P/ip"
( cd "$B" && PATH="$P:$PATH" sh "$S/testgetifaddr.sh" )
echo "rc=$?"        # -> testgetifaddr test OK，rc=0
```

实测读数（2026-10-01，miniupnpd 2.3.10）：① rc=1 无输出；②
`testgetifaddr test OK` rc=0。配方侧同一做法落在 `conanfile.py` 的
`_ensure_ip_tool()`，`conan create` 干净轮里 `make check` 4/4 全过
（日志 `testgetifaddr test OK` + `touch validategetifaddr`）。

## 关联条目

- 同族（名字对、实现不对 / 路径缺失）: notes/device-facts.md §一.14（OHOS Python 裸命令名无 PATH 搜索）、
  §一.18（taskset/patch 等 toybox 与 util-linux 双实现）、§一.26（toybox sh 对无斜杠命令做 PATH 搜索）
- `similar_to`: E091（OHOS linux/socket.h 与 sys/socket.h 头文件冲突）
