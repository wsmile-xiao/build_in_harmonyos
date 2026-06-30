# tf-summarize 编译笔记

## 基本信息

- 软件名: tf-summarize
- 版本: v0.3.20
- 类型: go 工具
- 编译日期: 2026-06-15

## 编译过程

### 编译方式

使用 go install 直接安装：
- Go 工具: `go install github.com/...@v0.3.20`
- Rust 工具: `cargo install tf-summarize`

### 验证

- 二进制文件: `~/go/bin/tf-summarize` 或 `~/.cargo/bin/tf-summarize`
- 功能验证: `tf-summarize --version` ✅

## 制品信息

- 制品包: `packaging/tf-summarize-v0.3.20-ohos-aarch64.tar.gz`
- 内容: `bin/tf-summarize`

## 备注

此软件通过 go install 直接安装成功，制品从已安装二进制打包创建。
