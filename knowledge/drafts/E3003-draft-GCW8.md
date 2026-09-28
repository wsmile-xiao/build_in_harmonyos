# DRAFT-E3003：ethtool_cmd_speed 符号级链接探测（glibc 有 / musl 缺）

- **触发实例**：samba 4.21.0 适配（2026-09-21，分支 feat/samba-4.21.0）
- **错误签名**：`ethtool_cmd_speed` 未定义 / `HAVE_ETHTOOL_CMD_SPEED` 缺失 / 链接阶段 undefined reference
- **类别**：detection（符号级探测）/ libc（glibc-musl 差异）/ socket
- **严重度**：2（按平台分支会误判或引入宏）

## 症状（可复现）

`ethtool_cmd_speed` 是由 glibc 提供的符号，libc（musl）无对应实现。若按"头文件有声明"判断，会误判为可用（声明存在但链接符号缺失）：

```text
# 头文件在（包含 linux/ethtool.h 之类），但链接时：
undefined reference to `ethtool_cmd_speed'
```

## 根因

`socket/interfaces` 的链路速率查询依赖 `ethtool_cmd_speed`，而该符号在 glibc 有、musl 无。若用平台宏（`#ifdef __OHOS__` / arch）分支，违反 R8/PF5，且掩盖真实链接语义。

## 方案

用**符号级链接探测**（waf 的 link check）定义 `HAVE_ETHTOOL_CMD_SPEED`：

```sh
# 引用该符号的小程序，由工具链真实链接结果决定
echo 'int ethtool_cmd_speed(void); int main(void){return ethtool_cmd_speed();}' | ${CC} -x c - -o /dev/null
```

链接成功 → 定义 HAVE_；链接失败 → 不定义 → 调用侧走降级（`*speed=0` 兜底）。对应 patch：`0003-lib-socket-wscript.patch`（新增符号级链接探测）+ `0002-lib-socket-interfaces.c.patch`（按 HAVE_ 分支 + 兜底）。

## 验证

```sh
OHOS 实测：Checking for HAVE_ETHTOOL_CMD_SPEED（由真实链接结果驱动），0 处 __OHOS__
```

## 边界 / 禁止

- 不按平台/架构宏判断（R8/PF5）；
- 头文件声明存在 ≠ 链接符号存在，必须用链接证据；
- 无符号时必须走真实降级路径，不伪造通过。

## 关联

- 触发 PR：!11515。
