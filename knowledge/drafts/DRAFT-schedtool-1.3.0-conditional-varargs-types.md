# 条件选择格式串时，拆开类型不同的变参调用

来源：[schedtool 1.3.0 原适配 PR #12447](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/12447)，orrkri，已于2026-09-28 16:49:13 +08合入；固定头 `a435baa2b4e9d3adea8c70859533ffc6dbb00d59`。本知识补交只含配对KV/MD，新增软件测试为0。

## 症状与触发条件

上游set_process在sched_setscheduler失败后，有两种诊断：合法policy范围0–5用%s输出名称，范围外用%d输出原始编号。原代码同时选择格式串和参数：

```c
decode_error((CHECK_RANGE_POLICY(policy) ? msg1 : msg2), pid,
             (CHECK_RANGE_POLICY(policy) ? TAB[policy] : policy));
```

固定原始归档schedtool.c:436在Linux x86_64 / GCC13.3.0严格构建中报告：

```text
error: pointer/integer type mismatch in conditional expression [-Werror]
cc1: all warnings being treated as errors
```

实际命令 `make -j1 CC=cc 'CFLAGS=-O2 -Wall -Wextra -Werror'`，make退出码2。该严格告警集合来自本地预检脚本，不能说成上游默认要求。OHOS原版编译对相同表达式只有[-Wconditional-type-mismatch] warning、RC0；KV只匹配上述失败error，不把warning或正常诊断当构建失败。

## 根因与修法

TAB[policy]为字符串指针，policy为运行期整数；它们不符合该条件表达式的C类型约束。分别选择%s/%d不会改变表达式本身的类型约束，也不建立两套不同的变参实参类型。

拆开完整调用，保持同一个范围判据、原格式串和退出语义：

```c
if (CHECK_RANGE_POLICY(policy))
    decode_error(msg1, pid, TAB[policy]);
else
    decode_error(msg2, pid, policy);
```

原适配补丁archives/s/schedtool/1.3.0/patches/0001-schedtool-c-portability.patch已含此修正。补丁同时移除冗余errno声明并初始化sched_param；本条只归纳两条格式契约，不把整个补丁都当变参修复。不要通过强制转换、整体关闭Werror或改动诊断文案来隐藏类型问题。人工检查格式串及全部参数后修正，rec_auto_fix=false。

## 既有验证与输入输出

在仅操作自身进程的既有H1隔离消费者中执行：

```sh
schedtool -M -1 0
# RC1，stdout包含：ERROR: could not set PID 0 to raw policy #-1 - value out of range / policy not implemented
schedtool -N -p 1 0
# RC1，stdout包含：ERROR: could not set PID 0 to N: SCHED_NORMAL - value out of range / policy not implemented
```

H1 v4 direct与Conan包内消费者的两条记录均为RC1、stderr为空，各2条断言passed。第一条policy=-1进入原始编号分支，第二条policy=0进入名称分支；判断依据唯一源码格式串及实际输出，没有插桩轨迹。日志中的ERROR是程序按预期拒绝非法参数，不是测试失败。

修后普通构建及H1 v4消费者通过，历史检查为17个功能场景加1个前提检查、103断言。没有修后相同-Werror全量构建结果，不能声称严格构建前后成对通过；源码已移除该条件表达式，实际两诊断路径正确。没有修前H1运行反例，不宣称证实了目标机崩溃、乱码或ABI错误。CPU19/高位affinity异常未由本补丁修复，本条不包含该问题。

## 可追溯原件

项目证据索引research/schedtool-2026-09-23/b-diagnostic-evidence-index-20261001.md绑定原件位置、环境、命令、退出码及SHA256；适配PR中公开源码及补丁，原始日志保留在项目归档。没有分别保存GCC stdout/stderr，以下为合并日志。

| 原件 | SHA256 |
|---|---|
| 原始schedtool_1.3.0.orig.tar.gz | 6628e4e805fab9c72b2daeb300c599d3de581f48eb21ce6caee3ae530b18450e |
| GCC baseline-build.log | b900f44ff56f8d2659ab395bdc58fe5501bf0c0b46b60e5ba56f6543c21512fb |
| status.txt | 1e62b1e26ff9037b267c5277c54e2fa372c5a99d19d6364a625e6e4dd9149c5d |
| 0001-schedtool-c-portability.patch | 32e86b369c3c653baf240258c263bc4bd255018e383b706803cab6a3b39712e7 |
| H1 functional-results.json | b4063929c4cfec980a52fed46123a17399b61d485e966c4edb84192b5c279a5d |
| H1 conan-functional-results.json | 04a77ec7e4bd989a43947634f3bda4e274743592569cfbafe21adcd047633d7f |

## 适用范围与近邻

适用于C诊断代码中按条件选择格式、相应参数包含不兼容指针/整数的情形；不限于鸿蒙，不涉及合法空指针常量、GNU零参数变参宏或libc输出差异。

- E063归纳Werror告警升级；本例补充真实类型约束的源码修法与两条诊断路径，不能直接用降级告警解决。
- E6401-draft-43B7处理GNU __VA_ARGS__ token-paste扩展，根因不同。
- icecream-cpp nullptr-format处理合法%p的libc输出差异，根因不同。
- 开放PR #13688 rio与#13779 unadf同步固定类型变化后的格式串；本例格式串原来各自正确，错误来自一个混合条件实参，需拆开调用。

当前排重来源固定官方main与开放Issue/PR只读快照；若维护者决定并入E063或相近条目，可合并本例证据，不重复申报同一知识积分。知识接受、合入及计分尚未发生。
