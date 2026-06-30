# goose 编译笔记

## 基本信息

- 软件名: goose
- 版本: v3.27.1
- 类型: go 工具
- 编译日期: 2026-06-15

## 编译过程

### 编译方式

使用 go install 直接安装：
- Go 工具: `go install github.com/...@v3.27.1`
- Rust 工具: `cargo install goose`

### 验证

- 二进制文件: `~/go/bin/goose` 或 `~/.cargo/bin/goose`
- 功能验证: `goose --version` ✅

## 制品信息

- 制品包: `packaging/goose-v3.27.1-ohos-aarch64.tar.gz`
- 内容: `bin/goose`

## 备注

此软件通过 go install 直接安装成功，制品从已安装二进制打包创建。
