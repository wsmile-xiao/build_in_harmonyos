# DRAFT-12283 — OHOS 上 /dev/uinput 的编译面可用性与运行时权限边界

## 错误特征

```
$ ydotoold -p "$TMPDIR/.ydotool_socket" -P 0600
You're advised to run this program as root, or YMMV.
failed to open uinput device: Permission denied      # exit code 2
```

能力探测（同一进程视角）：

```text
open("/dev/uinput", O_WRONLY) -> OSError errno 13 (EACCES)
stat("/dev/uinput")           -> EACCES（连 stat 都被拒）
cat /proc/misc | grep uinput  -> 223 uinput          # 内核支持存在
```

编译探测（与运行面相反）：

```text
$CC -c probe.c（#include <linux/uinput.h> + struct uinput_setup + UI_DEV_SETUP/UI_DEV_CREATE/UI_SET_*BIT）
-> 编译通过（OHOS native sysroot 头文件齐备）
```

## 触发条件

- 构建系统/工具: 任意（本实例 CMake + Conan；问题在运行时）
- 阶段: runtime（设备创建）/ testing（消费者测试分支判定）
- 场景: 程序通过 `/dev/uinput` 创建虚拟输入设备（uinput 注入）并以普通用户身份运行
- 环境: HarmonyOS PC aarch64；真机 shell/进程域 `u:r:hishell_hap:s0`（非系统域）

## 根因分析

1. **编译面与运行面分离**。OHOS native sysroot 完整提供 Linux uinput UAPI
   （`linux/uinput.h`、`linux/input-event-codes.h`，`struct uinput_setup`、
   `UI_DEV_SETUP`、`UI_DEV_CREATE`、`UI_SET_EVBIT/UI_SET_KEYBIT/UI_SET_RELBIT`
   等实测可编译），因此 uinput 客户端代码**零 API 改动**即可构建。
2. **运行面被安全策略阻断**。内核支持真实存在（`/proc/misc` 列出 `223 uinput`），
   但设备节点 `/dev/uinput` 对普通进程拒绝访问：`open(O_WRONLY)` 与 `stat` 均
   返回 `EACCES(13)`，`/dev/input` 同样被拒。设备节点的访问受 SELinux/ueventd
   管控，普通 HAP/shell 域不在允许清单内。
3. **失败位置明确**。`ydotoold` 在 `open("/dev/uinput", O_WRONLY)` 失败后立即
   `exit(2)` 并打印 `failed to open uinput device: Permission denied`，不会进入
   `UI_DEV_SETUP/UI_DEV_CREATE`；因此“设备创建失败”而非“事件被丢弃”。
4. **结论**：注入类工具在 OHOS 需要**系统级执行域**（root/system）才能完成
   虚拟设备创建；普通执行域下整条注入链不可用，这是平台安全模型边界，应用层
   无法绕过（也不应绕过）。

## 解决方案（推荐）

1. **诚实的能力探针**：运行时用真实 `open("/dev/uinput", O_WRONLY)` 判定分支，
   不要按平台名/内核名猜测，也不要照搬 Linux 的“通常需要 root”提示。
2. **消费者测试双分支**：
   - uinput 可用：守护进程输出 `READY`，`ydotool key 1:1` 经 socket 转发并返回 0；
   - uinput 被阻断：断言退出码 == 2 且 stderr 含 `failed to open uinput device`。
   两条分支都是真实断言，永远不出现“跳过即通过”。
3. **与 socket 侧解耦**：客户端线协议（`input_event` 字节流）用用户态
   AF_UNIX 数据报对端驱动断言，不依赖 `/dev/uinput`（配套草稿
   `DRAFT-12283-socket-dependent-tests-probe-gated-adaptation`）。
4. **文档如实标注**：README/notes/PR 正文写明“完整事件注入需系统级执行域”，
   不把平台边界包装成“已适配可用”。

## 禁止做法

- 不要用 `#ifdef __OHOS__` 空壳 stub 假装注入成功（R8/R40）。
- 不要为“让测试变绿”而跳过失败断言或伪造 READY/事件接收结果。
- 不要把 `EACCES` 当作构建缺陷去改源码（编译面本来就正常）。

## 验证

```bash
python3 -c 'import os; os.open("/dev/uinput", os.O_WRONLY)'   # PermissionError errno 13
cat /proc/misc | grep uinput                                   # 223 uinput
ydotoold -p "$TMPDIR/.ydotool_socket" -P 0600; echo "rc=$?"    # rc=2 + failed to open uinput device
$CC -c uinput_probe.c -o /tmp/uinput_probe.o && echo compile-ok  # 编译面可用
```

## 查重差异（与已有知识库）

- `E461`（AF_UNIX file-socket bind 被拒 / abstract 命名空间）：讲 **socket 绑定**；
  本条讲 **uinput 设备节点权限**，是同一“注入链”上的另一道独立边界。
- `E024`（use-tcp-socket）：AF_UNIX → TCP 的替代方案；对 uinput 无替代（必须设备节点）。
- `E002/E052`（/tmp 只读）：文件系统边界；与本条无关。
- `DRAFT-libevdev-1.13.7-…`（UAPI 头探测 / needs-uinput 测试约束）：输入**消费**库
  的构建与测试约束；本条是输入**注入**工具的运行时权限面。
- `DRAFT-ohos-syscall-capability-matrix-fork-probe`：syscall 能力矩阵探测；
  本条给出“设备节点权限 + 探针式双分支测试”的具体范式。
- `ydotool`/`uinput` 在正式索引（index.tsv 540 条）与既有草稿中 0 命中。

## 关联条目

- similar_to: E461（socket 绑定边界）、E024（AF_UNIX 替代）、E052（文件系统边界）
- 配套草稿: DRAFT-12283-socket-dependent-tests-probe-gated-adaptation
