# DRAFT-ohos-proc-fd-symlink-invisible：OHOS 下 /proc/$BASHPID/fd/N 符号链接不可见→fd dup 测试 { : 10>&"$1"; }

> Contributor: blesh-0.4.0-git20250806.8060b7a 适配 | Status: Draft | Updated: 2026-08-24
> Source: archives/b/blesh/0.4.0-git20250806.8060b7a（make check 实测 + 本地修复验证）

## 现象

ble.sh 上游测试 `ble/fd#is-open` 1/2 两个用例失败。该函数检测一个 fd
是否处于打开状态，原实现：

```bash
function ble/fd#is-open { [[ $1 && -e /proc/$BASHPID/fd/$1 ]]; }
```

OHOS HMDFS/沙箱环境下 `/proc/$BASHPID/fd/N` 符号链接**不可见**——fd 实际
处于打开状态（`10>&"$1"` 能成功 dup），但 `[[ -e ... ]]` 检查返回假。
两个用例因此 fail。

## 主从根因

- **主根因**：OHOS 下 /proc/$BASHPID/fd/N 符号链接不可见（procfs 行为
  差异，归轴 1 平台能力边界）。fd 实际打开与 `-e` 检查结果不一致。
- 无附加从因：非权限问题（fd 本身可 dup）、非路径问题（/proc 存在，
  只是 fd/N 符号链接不可见）。

## 与现有知识的关系

- knowledge/graph 现有条目不覆盖 /proc fd 符号链接可见性——本主题无覆盖。
- 跨库可复用：任何用 `/proc/self/fd/N` 或 `/proc/$BASHPID/fd/N` 检测
  fd 打开状态的 bash 脚本/库（管道检测、fd 复用、重定向管理）在 OHOS
  都会命中此差异。

## 方案

改用"尝试 dup"检测 fd 打开状态（上游自身已有兼容 fallback 模式，ble.sh
实现里 `.upgrade` 覆盖机制支持替换实现——环境适配，不改上游测试断言）：

```bash
# 适配（配方内生成 out/ble.sh 时文本替换，不改测试用例）：
s = s.replace('''  function ble/fd#is-open { [[ $1 && -e /proc/$BASHPID/fd/$1 ]]; }
  function ble/fd#is-open/.upgrade { builtin unset -f "$FUNCNAME"; }''',
              '''  function ble/fd#is-open { { builtin : 10>&"$1"; } 2>/dev/null; }
  function ble/fd#is-open/.upgrade { builtin unset -f "$FUNCNAME"; }''')
```

原理：`{ builtin : 10>&"$1"; }` 尝试把 fd $1 dup 到 fd 10——成功（返回
0）说明 fd 打开，失败（dup 返回非零，stderr 已 2>/dev/null 吞掉）说明
关闭。选择 fd 10 是因为避开测试自身使用的 fd 9（上游测试环境约定）。

## 验证证据

- 本地 OHOS 环境 make check：替换前 ble/fd#is-open 1/2 两个 fail；替换后
  7830/7830 全过（100%）。
- CI 日志（ci_blesh6186b.log）：JC pass、7830/7830、L0/L1/L4/L5 pass、
  Success 1 100%。

## 适用场景

- 纯 Bash 库/工具在 OHOS 上检测 fd 打开状态。
- 任何依赖 /proc/$BASHPID/fd 符号链接做探测的脚本在 OHOS 上的适配。

## 禁止做法

- 不要删掉 fd 检测直接返回"打开"——会掩盖 fd 真实状态（关闭的 fd 被
  误判打开导致后续写入失败）。
- 不要依赖 /proc/$BASHPID/fd/N 的 `-e` 检查在 OHOS 上的结果——不可见
  不代表关闭，需用 dup 语义探测。
