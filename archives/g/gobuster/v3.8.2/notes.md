# gobuster 编译笔记

## 基本信息
- 软件名: gobuster
- 版本: v3.8.2
- 类型: Go 工具
- 编译日期: 2026-06-15

## 编译过程

### 源码获取
git clone https://github.com/OJ/gobuster.git

### 编译命令
```bash
export GOPROXY=https://goproxy.cn,direct
export CGO_ENABLED=0
go build -o gobuster .
```

### 验证
```bash
./gobuster --version
# gobuster version 3.8.2
```

## 制品信息
- 制品包: `packaging/gobuster-v3.8.2-ohos-aarch64.tar.gz`
- 内容: `bin/gobuster`
