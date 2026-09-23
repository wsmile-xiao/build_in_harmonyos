# E337 — HarmonyOS file_manager 挂载点 (hmdfs) 无法创建 Unix socket

## 错误特征

服务/守护进程在用户主目录（`/storage/Users/currentUser/`）下绑定 Unix socket 时失败：

```
Error: Os { code: 1, kind: PermissionDenied, message: "Operation not permitted" }
```

典型实例（herdr 0.8.2，鸿蒙 PC）：

```bash
$ herdr server          # 默认配置目录 ~/.config/herdr
Error: Operation not permitted    # server 启动失败
$ herdr status server
status: not running
socket: /storage/Users/currentUser/.config/herdr/herdr.sock   # socket 从未创建
```

## 触发条件

- 平台: HarmonyOS/OpenHarmony PC（arm64）
- 阶段: runtime（服务启动 / daemon / IPC socket bind）
- 前置: 工具把 socket 路径放在用户主目录下（默认 `~/.config/<app>/`、`~/.local/state/` 等）
- 典型工具: herdr server、tmux 类多路复用器、本地 socket server、语言服务器

## 根因分析

鸿蒙的用户主目录 `/storage/Users/currentUser/` 由 **file_manager hmdfs 挂载**提供。
hmdfs 不支持创建 Unix domain socket：`bind()` 直接返回 `EPERM`（Operation not permitted）。
这与 SELinux 无关（chmod/chown 也无效），是**文件系统本身不支持 socket 类型文件**。

任何在默认用户目录下创建 socket 的服务型工具都会在启动时失败。

## 解决方案

### 推荐方案：重定向 XDG 目录到支持 socket 的目录

把工具的配置/状态目录指到**应用数据区**（如 `/data/storage/el2/base/...`，owner 正常且支持 socket）：

```bash
export XDG_CONFIG_HOME=/data/storage/el2/base/files/home_dir/.config
export XDG_STATE_HOME=/data/storage/el2/base/files/home_dir/.state
```

### 回退方案：工具级 socket 路径

如果工具提供 socket 路径配置（如 herdr 的 `HERDR_SOCKET_PATH`），只重定向 socket：

```bash
export HERDR_SOCKET_PATH=/data/storage/el2/base/cache/herdr.sock
```

### 禁止做法

- ❌ `chmod 777 ~/.config/xxx` / `chown` socket 文件 —— hmdfs 本身拒绝 bind，改权限无效
- ❌ `ln -sf` 软链接 socket —— 挂载点不支持 socket，链接也无济于事

## 验证

```bash
# 失败复现（默认路径）
herdr server                      # → Operation not permitted

# 修复验证（XDG 重定向）
export XDG_CONFIG_HOME=/data/storage/el2/base/files/home_dir/.config
export XDG_STATE_HOME=/data/storage/el2/base/files/home_dir/.state
herdr server &
herdr status server               # → status: running, socket 正常创建
```

## 关联条目

- 相关: [E002](E002.md)（鸿蒙 /tmp 只读）、[E046](E046.md)（chmod 不生效，SELinux 限制）
- 本条目侧重：file_manager 挂载点**文件系统层面**不支持 socket（与 E002/E046 的权限/挂载限制同族）

## 来源

- herdr 0.8.2 HarmonyOS PC 适配（2026-08-25 实测）
- 经验沉淀: archives/h/herdr/0.8.2/notes.md
