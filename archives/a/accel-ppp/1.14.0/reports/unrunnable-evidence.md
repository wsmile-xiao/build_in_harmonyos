# 上游未通过用例「无法运行」证据链 — accel-ppp 1.14.0

> **目的**：按 PR 审查意见（规则 4）补充「无法运行」技术论证——对 10 个未通过的上游 pytest
> 用例，给出**报错位置、修复尝试证据链、系统级证明**，说明其阻塞根因属 OHOS 平台/权限前置
> 缺失，而非适配代码缺陷。所有证据均为 2026-08-19 在 HarmonyOS HongMeng Kernel aarch64
> （OHOS）验证环境实测。
>
> 执行环境：上游 tag `1.14.0` 的 `tests/`，pytest 9.1.1，已构建的
> `accel-pppd`/`accel-cmd`（OHOS aarch64，32 个补丁）。

## 0. 系统级证据（适用于全部 10 个用例）

| 证据项 | 命令/检查 | 结果 |
|--------|-----------|------|
| 进程能力 | `grep CapEff /proc/self/status` | `000000000000002a` = **CAP_DAC_OVERRIDE, CAP_FOWNER, CAP_KILL**（无 CAP_NET_ADMIN、CAP_NET_RAW、CAP_SYS_MODULE、CAP_SYS_ADMIN） |
| /dev/ppp 权限 | `ls -l /dev/ppp` | `crw-rw---- 1 root root 108, 0` — 仅 root/root 可读写；本进程非 root，open() 返回 `EACCES` |
| AF_PACKET raw socket | `socket(AF_PACKET, SOCK_RAW, 0x8863)` | `PermissionError [Errno 13] Permission denied`（需 CAP_NET_RAW） |
| veth/netns | `unshare -n true` | `unshare: inaccessible or not found`；且无 CAP_NET_ADMIN 无法创建 veth pair |
| 缺失命令 | `command -v ip pppd dhclient pppoe-discovery` | 全部无（busybox 有 ip/udhcpc 但无 CAP_NET_ADMIN/RAW，仍无法建 veth/raw socket） |
| 内核模块 | `ls -d /sys/module/vlan_mon /sys/module/ipoe` | 均 `No such file or directory` |

> 这些是 OS 内核/权限层的确定性约束：`/sys/module/*` 不存在且无 CAP_SYS_MODULE 无法加载；
> veth/netns/raw socket 需要 CAP_NET_ADMIN/CAP_NET_RAW；`/dev/ppp` 为 root 专属。
> 用户态适配代码无法改变以上任何一项。

---

## 1. 环境错误（7 个）：veth/netns 建立失败 — `FileNotFoundError: 'ip'`

上游这些用例的 fixture `veth_pair_netns`（`tests/conftest.py` → `common/veth.create_veth_pair_netns`）
在 setup 阶段调用 `ip` 命令创建 veth pair 与网络命名空间。

**报错位置（pytest 实测，accel-pytest-full.log）**：

```text
ERROR at setup of test_pppoe_discovery
E       FileNotFoundError: [Errno 2] No such file or directory: 'ip'
../../../../../usr/local/lib/python3.12/subprocess.py:1804: FileNotFoundError
```

同样报错逐字出现在以下 7 个用例的 setup：

| 用例 | 报错 |
|------|------|
| test_pppoe_discovery | `FileNotFoundError: 'ip'`（setup） |
| test_pppoe_session_chap_secrets | `FileNotFoundError: 'ip'`（setup） |
| test_pppoe_session_wo_auth | `FileNotFoundError: 'ip'`（setup） |
| test_pppoe_vlan_mon | `FileNotFoundError: 'ip'`（setup） |
| test_ipoe_shared_session_chap_secrets | `FileNotFoundError: 'ip'`（setup） |
| test_ipoe_shared_session_lua_chap_secrets | `FileNotFoundError: 'ip'`（setup） |
| test_ipoe_shared_session_wo_auth | `FileNotFoundError: 'ip'`（setup） |

**修复尝试证据链**：

1. **尝试提供 `ip` 命令**：busybox 提供 `ip`/`udhcpc`/`unshare`，但随后验证 veth 创建需要
   `CAP_NET_ADMIN`，而 `CapEff` 无该位 → 仍无法创建 veth pair / netns（`AF_PACKET` raw socket
   亦因无 CAP_NET_RAW 被拒）。结论：**工具可替代，权限不可替代**。
2. **尝试提供 pppd/dhclient/pppoe-discovery**：设备无这些工具，且 PPPoE 会话用例还需 raw
   socket（无 CAP_NET_RAW）与 `/dev/ppp`（root 专属 EACCES）→ 即使装工具也无法完成会话。
3. **未修改上游测试**：这些是环境 fixture 依赖，不属于可固化的适配修复。

**结论**：阻塞根因是 OHOS 验证环境的**特权网络能力缺失**（无 CAP_NET_ADMIN/CAP_NET_RAW、
无 ip 命令），需具备这些条件的真机/特权环境复测；非适配代码缺陷。

---

## 2. 失败（2 个）：内核模块不存在

| 用例 | 断言 | 实测 |
|------|------|------|
| test_ipoe_kernel_module_loaded | `assert os.path.isdir("/sys/module/ipoe")` | `False`（目录不存在） |
| test_vlan_mon_kernel_module_loaded | `assert os.path.isdir("/sys/module/vlan_mon")` | `False`（目录不存在） |

**报错位置**：

```text
>       assert os.path.isdir("/sys/module/ipoe")
E       AssertionError: assert False
```

**修复尝试证据链**：

1. 这两个用例检测**内核模块是否加载**；OHOS 内核未内置 `ipoe`/`vlan_mon` 模块，且本进程无
   `CAP_SYS_MODULE` 无法 insmod。
2. 用户态等效验证已补充：`test_package/smoke_test.py` 的 `check_module_integrity` 以真实
   全模块配置启动 accel-pppd，断言日志无 `failed to load`（对应模块 `libipoe.so`/
   `libvlan-mon.so` 及其 DT_NEEDED 依赖可加载）— 实测通过。

**结论**：阻塞根因是 OHOS 内核缺 `ipoe`/`vlan_mon` 模块（内核能力前置），需在加载这些模块
的内核/真机环境复测；用户态模块加载完整性已通过等效测试证明。

---

## 3. 跳过（1 个）：上游自身 skip

| 用例 | 原因 |
|------|------|
| test_pppoe_pado_delay | `pytestmark = pytest.mark.skipif(not support_pppoe_discovery_a_t(), ...)` — 环境无支持 `-a`/`-t` 的 pppoe-discovery，上游源码自行跳过 |

**报错位置**：无报错，上游源码主动跳过（`tests/accel-pppd/pppoe/test_pppoe_pado_delay.py:22-24`）。

**结论**：该用例在上游设计上即为条件跳过，与适配无关；不统计为失败。

---

## 4. 汇总

| 类别 | 数量 | 根因 | 是否适配可修 |
|------|------|------|--------------|
| 环境错误 | 7 | veth/netns 需 CAP_NET_ADMIN + ip 命令；会话需 raw socket/pppd//dev/ppp | 否（权限/工具前置） |
| 失败 | 2 | 内核无 ipoe/vlan_mon 模块（无 CAP_SYS_MODULE） | 否（内核前置；用户态等效已验证） |
| 跳过 | 1 | 上游条件跳过（无 pppoe-discovery -a/-t） | 否（上游设计） |

通过：**7/17（41.2%）**。已通过用例含：test_accel_cmd_version、test_accel_cmd_non_existent_host、
test_accel_cmd_mcast_host、test_accel_cmd_commands、test_accel_pppd_version、
test_load_all_modules、test_pcre_negative_cases（后两者在模块 DT_NEEDED 修复后由失败转通过）。

**真实结论**：当前 OHOS 验证环境不具备特权网络/内核模块/PPPoE 对端等前置条件，真实
PPP/PPPoE 会话尚未验证；需在具备上述条件的 OHOS 真机/特权环境复测后回填真实通过率。
