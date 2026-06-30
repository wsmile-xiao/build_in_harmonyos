# faas-cli 编译笔记

## 基本信息

- 软件名: faas-cli
- 版本: 0.0.0-20260402103051
- 类型: go 工具
- 编译日期: 2026-06-15

## 编译过程

### 编译方式

使用 go install 直接安装：
- Go 工具: `go install github.com/...@0.0.0-20260402103051`
- Rust 工具: `cargo install faas-cli`

### 验证

- 二进制文件: `~/go/bin/faas-cli` 或 `~/.cargo/bin/faas-cli`
- 功能验证: `faas-cli --version` ✅

## 制品信息

- 制品包: `packaging/faas-cli-0.0.0-20260402103051-ohos-aarch64.tar.gz`
- 内容: `bin/faas-cli`

## 备注

此软件通过 go install 直接安装成功，制品从已安装二进制打包创建。
