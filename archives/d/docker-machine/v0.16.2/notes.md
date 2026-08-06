# docker-machine v0.16.2 适配笔记

## 编译环境
- 构建系统: Go (GOPATH 模式, dep 依赖管理, vendor 目录)
- 编译日期: 2026-08-06
- 编译器: Go 1.26.5 (Harmonybrew), CGO_ENABLED=1
- 状态: published

## 编译步骤

1. 从 GitHub 下载 v0.16.2 源码包
2. 清理源码中的断链符号链接（vendor/github.com/docker/docker 下的 .pem 和 CONTRIBUTING.md）
3. 设置 GOPATH 并将源码链接到 GOPATH/src/github.com/docker/machine
4. 使用 GO111MODULE=off 模式编译（项目使用 dep 而非 go modules）

```bash
export GOPATH=/storage/Users/currentUser/go
ln -sf $BUILD_SRC_DIR $GOPATH/src/github.com/docker/machine
cd $GOPATH/src/github.com/docker/machine
GO111MODULE=off CGO_ENABLED=1 GOOS=linux GOARCH=arm64 \
  go build -ldflags="-s -w -X github.com/docker/machine/version.GitCommit=v0.16.2-ohos" \
  -o bin/docker-machine ./cmd/docker-machine
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build copytree 失败 | HMDFS 不支持硬链接 (os.link) | 手动 cp -rL 复制，删除断链后重试 |
| 2 | 源码中断链 | vendor/github.com/docker/docker 下的 .pem 和 CONTRIBUTING.md 是断链 | 删除断链文件 |
| 3 | go.mod not found | 项目使用 dep (Gopkg.toml) 而非 go modules | 使用 GO111MODULE=off + GOPATH 模式 |

## 源码修改

无补丁 — 上游 v0.16.2 源码在 HarmonyOS 上可直接编译通过，所有驱动完整保留。

## 依赖版本

- Go 1.26.5 (Harmonybrew)
- 无外部 C/C++ 依赖

## 验证结果

```bash
$ docker-machine version
docker-machine version 0.16.2, build v0.16.2-ohos

$ go test -short ./cmd/...
# 仅一个环境相关测试失败 (TestStorePathSetCorrectly, 依赖 MACHINE_STORAGE_PATH 环境变量)
```

## 注意事项

- docker-machine 项目已归档（archived），v0.16.2 是最后版本
- 与之前 homebrew 版本不同，本次编译保留所有驱动，未做任何裁剪
- vendor 目录中所有依赖包（含 cloud SDK）均编译通过
---

**编译结束**: 2026-08-06 07:48
**最终状态**: built
