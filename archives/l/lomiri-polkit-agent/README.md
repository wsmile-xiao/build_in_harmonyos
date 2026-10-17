# lomiri-polkit-agent

Lomiri 的 PolicyKit 会话认证代理：向 polkit 注册 `org.freedesktop.PolicyKit1.AuthenticationAgent`
实现，在用户会话内弹出认证对话框。属 D-Bus 激活的会话服务（非命令行工具），产物为
`bin/lomiri-polkit-agent/policykit-agent` 与 systemd user unit。

**官网**: https://gitlab.com/ubports/development/core/lomiri-polkit-agent

**分类**: system/application

**开源信息**: 上游仓库 `https://gitlab.com/ubports/development/core/lomiri-polkit-agent`，
许可 **GPL-3.0**（上游 `COPYING`，随包分发）；源码取自上游官方 GitLab 归档
`/-/archive/0.3.3/lomiri-polkit-agent-0.3.3.tar.gz`（sha256 `96167c491cbb17d800e7037c0b038931104423e5d916069f34661231ccdba028`），
无 fork、无镜像改写。

## 版本列表

- 0.3.3 (2026-09-29) - built（application：bin/lomiri-polkit-agent/policykit-agent 服务二进制 + systemd user unit）

## 依赖

- polkit >= 124.1（`polkit-agent-1`：libpolkit-agent-1 + polkit-agent-1.pc，来自本仓库 polkit/124.1）
- glib（`gio-2.0`：GDBus 会话总线）
- libnotify（桌面通知）
- properties-cpp（D-Bus 属性封装）

## 编译说明

使用 CMake（C++17）构建。推荐配置选项：

```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF
```

`-DBUILD_TESTING=OFF` 关闭上游 `tests/`：其依赖 Ubuntu 专有的 GMock（硬编码 `/usr/src/gtest`）
与 `dbustest-1`，OHOS 侧不可用（清点与不运行原因见 `0.3.3/notes.md` 上游测试申报表，R51）。

两个补丁：`0001` 用 `if(COMMAND ...)` 守卫 Ubuntu cmake-extras 的
`add_formatcode_target()`/`ENABLE_COVERAGE_REPORT()`（否则非 Ubuntu 主机 configure 即失败）；
`0002` 为服务二进制补 `--version`/`--help` 分支，使其可在无 session bus/polkitd 的环境被冒烟测试。

## 执行说明

服务由 D-Bus 会话总线按 `lib/systemd/user/lomiri-polkit-agent.service` 激活，不是用户直接调用的
命令行工具，因此不导出 `bindirs`；其运行需要 session bus + polkitd + 认证对话框后端，属运行环境
能力而非本包产物（详见 `0.3.3/README.md` §5）。
