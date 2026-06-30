# logcli 3.7.2 编译笔记

## 编译信息
- 源码: https://github.com/grafana/loki/archive/refs/tags/v3.7.2.tar.gz
- 版本: 3.7.2
- 平台: OpenHarmony aarch64
- 构建系统: Go (vendor mode)
- 编译器: go1.26.0

## 编译命令
```bash
cd cmd/logcli
go build -v -mod=vendor \
  -ldflags="-s -w -X github.com/grafana/loki/v3/pkg/util/build.Version=3.7.2 -X github.com/grafana/loki/v3/pkg/util/build.Branch=main" \
  -o logcli .
```

## 特殊处理
- 依赖 Go 1.26.0（项目要求 Go 1.26.2）
- CGO_ENABLED=0 静态编译
- 使用 vendor 模式避免网络依赖

## 验证结果
```
logcli, version 3.7.2 (branch: main, revision: unknown)
  build date:       2026-05-28T13:03:33Z
  go version:       go1.26.0
  platform:         linux/arm64
```

## 编译日期
2026-05-28
