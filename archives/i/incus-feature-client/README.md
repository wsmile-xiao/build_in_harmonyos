# incus-feature-client

Incus 是 LXD 项目的社区分支，提供系统容器与虚拟机管理能力。本仓库适配的是 **Incus 的命令行客户端** `incus`（`/usr/bin/incus`）。

## 说明

`incus-feature-client` 是 Alpine 源包 **`incus-feature`**（Incus「Feature branch」打包）的二进制子包：
其 APKBUILD 的 `client()` 函数把 `usr/bin/incus` 单独拆出，即本目标库。上游源码为
[github.com/lxc/incus](https://github.com/lxc/incus) 的 tag **v7.2.0**（Go module `github.com/lxc/incus/v7`）。

- 客户端 `incus` 为**纯 Go**：`cmd/incus` 的 import 闭包不含任何 cgo/第三方原生库，
  因此以 `CGO_ENABLED=0` 交叉编译为 aarch64 静态 ELF，在 HarmonyOS（Linux 兼容内核）上直接运行。
- 服务端守护进程 `incusd` 需要 `CGO_ENABLED=1` 与 `liblxc`/`cowsql`/`libsqlite3`/`libudev` 等，
  HarmonyOS 上不可用 —— **不在本子包范围内**（与本仓库既有 `archives/i/incus` 7.1.0 的结论一致）。

## 已适配版本

- 7.2.0 (2026-10-10)

## 依赖

- Go 1.25.10（配方内自举下载，不依赖宿主机预装）

## 特性

- 连接 Incus 守护进程（本地 unix socket 或远程 HTTPS）管理实例
- 实例生命周期：`launch` / `list` / `start` / `stop` / `delete` …
- 镜像、网络、存储、项目、配置、快照、远程仓库等完整 CLI surface

## 使用方法

```bash
# 版本
incus --version         # 7.2

# 查看帮助
incus --help

# 列出容器
incus list

# 启动容器
incus launch images:ubuntu/24.04 my-container

# 进入容器
incus exec my-container -- bash

# 管理虚拟机
incus launch images:ubuntu/24.04 my-vm --vm
```

## 注意事项

- 以 `CGO_ENABLED=0` 编译，产物为静态 aarch64 ELF。
- 运行时需连接一个 Incus 守护进程（`incusd`）；本仓库仅提供客户端。
- OHOS 上 ELF 必须带 `.codesign` 段才能执行，构建阶段已自动用 `binary-sign-tool` 签名。
- 无源码修改，无补丁文件（`patches: []`）。
