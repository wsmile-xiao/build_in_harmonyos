# slackdump 编译笔记

## 基本信息
- 软件名: slackdump
- 版本: v4.0.0
- 类型: Go 工具
- 编译日期: 2026-06-15

## 编译过程

### 源码获取
git clone https://github.com/rusq/slackdump.git

### 编译命令
```bash
export GOPROXY=https://goproxy.cn,direct
export CGO_ENABLED=0
go build -o slackdump ./cmd/slackdump
```

### 验证
```bash
./slackdump version
# Slackdump v4
```

## 制品信息
- 制品包: `packaging/slackdump-v4.0.0-ohos-aarch64.tar.gz`
- 内容: `bin/slackdump`
