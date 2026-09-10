# herdr

## 简介
终端工作区管理器（Agent 多路复用器），专为 AI 编码 agent 设计的终端环境。
类似 tmux 但面向 AI agent：持久的后台服务器、agent 状态感知、socket API 控制。

## 主页
- 官网: https://herdr.dev
- 源码: https://github.com/herdrdev/herdr

## OHOS 适配
- 构建系统: Rust/cargo (aarch64-unknown-linux-ohos)
- vendored libghostty-vt 需 Zig 0.15.2 构建
- Zig 0.15.2 无 OHOS libc headers，用 aarch64-linux-musl target 替代（libc 为 musl 系）
- 鸿蒙设备上 zig 生成的中间 ELF（build runner、工具）需 binary-sign-tool 签名后方可执行
- 产物: 23MB 动态链接 ELF (musl)，`herdr --version` 验证通过
- 核心功能: server 后台运行、workspace 创建/列表 API 均正常

## 鸿蒙安装后必配（harmonybrew caveats 参考）

`herdr server` 在鸿蒙默认配置目录（`~/.config/herdr`，file_manager/hmdfs 挂载）**无法创建 Unix socket**，启动报 `Operation not permitted`。必须重定向 XDG 目录到支持 socket 的位置：

```bash
# 写入 ~/.zshrc（持久）
export XDG_CONFIG_HOME=/data/storage/el2/base/files/home_dir/.config
export XDG_STATE_HOME=/data/storage/el2/base/files/home_dir/.state
```

`herdr --remote` 若报 `muxclient: master hello exchange failed`（鸿蒙 OpenSSH 不支持 ControlMaster），在 `~/.config/herdr/config.toml` 加：

```toml
[remote]
manage_ssh_config = false
```