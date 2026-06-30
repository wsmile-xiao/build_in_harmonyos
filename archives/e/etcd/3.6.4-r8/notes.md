# etcd 3.6.4-r8 编译笔记

## 任务信息

- 软件名称: etcd
- 版本: 3.6.4-r8
- 分类: Part2 #38
- 安装量: 2418
- 项目类型: Go

## 编译环境

- Go 版本: go1.26.0 linux/arm64
- GOPROXY: https://goproxy.cn,direct
- CGO_ENABLED: 0 (静态编译)
- TMPDIR: /data/storage/el2/base/cache

## 编译过程

### 1. 源码获取

由于网络 SSL 证书问题，无法直接从 GitHub 或 proxy.golang.org 下载。采用以下方法：
- 使用 `go mod download go.etcd.io/etcd/v3@v3.6.4` 从 goproxy.cn 下载主模块
- 使用 `go mod download` 下载所有子模块：
  - go.etcd.io/etcd/api/v3@v3.6.4
  - go.etcd.io/etcd/client/pkg/v3@v3.6.4
  - go.etcd.io/etcd/client/v3@v3.6.4
  - go.etcd.io/etcd/etcdctl/v3@v3.6.4
  - go.etcd.io/etcd/etcdutl/v3@v3.6.4
  - go.etcd.io/etcd/pkg/v3@v3.6.4
  - go.etcd.io/etcd/server/v3@v3.6.4
  - go.etcd.io/etcd/tests/v3@v3.6.4

### 2. 源码解压

etcd 使用 go.mod replace 指令，将子模块替换为本地目录。需要手动解压所有子模块到正确位置：
- api → ./api
- client/pkg → ./client/pkg
- client/v3 → ./client/v3
- etcdctl → ./etcdctl
- etcdutl → ./etcdutl
- pkg → ./pkg
- server → ./server
- tests → ./tests

### 3. 编译

由于 etcd 的 go.mod 使用 replace 指令，无法直接使用 `go install`。需要在每个子模块目录中单独编译：

```bash
cd server && go build -v -mod=mod -trimpath -ldflags="-s -w" -o bin/etcd .
cd etcdctl && go build -v -mod=mod -trimpath -ldflags="-s -w" -o bin/etcdctl .
cd etcdutl && go build -v -mod=mod -trimpath -ldflags="-s -w" -o bin/etcdutl .
```

### 4. ELF 签名

使用 `ohc-run.py sign-elf` 对所有二进制文件进行签名，使其可以在鸿蒙系统上执行。

### 5. 验证

所有二进制文件验证通过：
- etcd --version: 3.6.4 ✅
- etcdctl version: 3.6.4 ✅
- etcdutl version: 3.6.4 ✅

## 编译产物

| 文件 | 大小 | 说明 |
|------|------|------|
| etcd | 24.67 MB | 服务器 |
| etcdctl | 16.47 MB | 客户端工具 |
| etcdutl | 16.35 MB | 管理工具 |

预编译包: etcd-3.6.4-r8-ohos-aarch64.tar.gz (55 MB)

## 质量门禁

G0-G4 全部通过 ✅

## 注意事项

1. etcd 是 Go 项目，使用 replace 指令管理子模块，需要特殊处理
2. 需要从 goproxy.cn 下载所有子模块并手动解压
3. CGO_ENABLED=0 确保静态编译，无外部依赖
4. 所有二进制文件需要 ELF 签名才能在鸿蒙系统上执行

---
编译完成: 2026-05-29 16:15
