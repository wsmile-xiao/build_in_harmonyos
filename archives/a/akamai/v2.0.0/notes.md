# akamai 编译笔记

## 基本信息

- 软件名: akamai
- 版本: v2.0.0
- 类型: go 工具
- 编译日期: 2026-06-15

## 编译过程

### 编译方式

使用 go install 直接安装：
- Go 工具: `go install github.com/...@v2.0.0`
- Rust 工具: `cargo install akamai`

### 验证

- 二进制文件: `~/go/bin/akamai` 或 `~/.cargo/bin/akamai`
- 功能验证: `akamai --version` ✅

## 制品信息

- 制品包: `packaging/akamai-v2.0.0-ohos-aarch64.tar.gz`
- 内容: `bin/akamai`

## 备注

此软件通过 go install 直接安装成功，制品从已安装二进制打包创建。
