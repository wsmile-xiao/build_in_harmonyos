# atlantis

Terraform Pull Request Automation — 在 Pull Request 上自动执行 `terraform plan` / `terraform apply` 的协作服务。

## 版本

- 0.46.0 (2026-08-11) - built ✅

## 描述

atlantis 是 Terraform 工作流自动化工具，支持：
- 在 PR 评论中触发 `plan` / `apply`
- GitHub / GitLab / Bitbucket 等 VCS 集成
- 项目级配置与锁管理
- OpenTofu (.tofu) 支持（0.46.0 新增）

## 关键编译信息

- 构建系统: Go (custom)
- 无 configure/make 流程，直接 `go build`
- CGO_ENABLED=0 静态编译（纯 Go，无 C 依赖）
- 产物: `atlantis` 可执行文件（服务端 + CLI）
