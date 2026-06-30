# precious 编译笔记

## 基本信息

- 软件名: precious
- 版本: 0.10.2
- 类型: rust 工具
- 编译日期: 2026-06-15

## 编译过程

### 编译方式

使用 rust install 直接安装：
- Go 工具: `go install github.com/...@0.10.2`
- Rust 工具: `cargo install precious`

### 验证

- 二进制文件: `~/go/bin/precious` 或 `~/.cargo/bin/precious`
- 功能验证: `precious --version` ✅

## 制品信息

- 制品包: `packaging/precious-0.10.2-ohos-aarch64.tar.gz`
- 内容: `bin/precious`

## 备注

此软件通过 rust install 直接安装成功，制品从已安装二进制打包创建。
