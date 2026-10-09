# k3d

k3d 是一个在 Docker 中运行 k3s 的轻量级工具，用于创建本地 Kubernetes 开发集群。
它在不安装 Docker（k3s 通常要求）的前提下，通过 `k3d cluster create` 一条命令
秒级创建一个多节点 k3s 集群，是本地 Kubernetes 开发与测试的常用 CLI。

## 功能概述

- `k3d cluster create <name>` — 创建 k3s 集群节点
- `k3d cluster delete|list|start|stop` — 管理集群生命周期
- `k3d node create` — 增删节点/代理
- `k3d registry create` — 管理本地 registry
- `k3d image import` — 将本地镜像导入集群
- `k3d kubeconfig get|merge` — 获取 / 合并 kubeconfig
- `k3d config` — 配置迁移 / 校验 / 转换
- `k3d version` — 显示 k3d 与默认 k3s 版本

## OHOS 适配

- 纯 Go CLI（`github.com/k3d-io/k3d/v5`），go.work workspace + 自带 `vendor/`，
  静态构建（CGO_ENABLED=0），可运行于 HarmonyOS PC aarch64。
- go.mod / go.work 要求 `go 1.26.3`；依赖全部由仓库 `vendor/` 离线承载
  （`-mod=vendor`），构建与测试不依赖 GOPROXY 拉取。
- 上游官方测试为 `go test -v ./...`（23 个顶层 Test* 函数）。
- hmbs 预检 conan-create 沙盒只注入 cmake/make/ninja/python3，不含 Go 工具链；
  设备无 go 或过旧时，配方自动从 aliyun Go 镜像 bootstrap go1.26.3 工具链并
  ELF 签名（vibecheck/1.7.7 先例），随后真实运行上游 `go test -v ./...`
  （23 个顶层 Test* 函数）。

## 依赖关系

- 编译依赖：Go 工具链（>= 1.26.3）
- 运行依赖：无（纯 Go 静态二进制）；实际管理集群需目标机器有 Docker

## 参考资料

- 上游源码：https://github.com/k3d-io/k3d
- 官网：https://k3d.io
- 版本：v5.9.0
- 许可证：MIT
