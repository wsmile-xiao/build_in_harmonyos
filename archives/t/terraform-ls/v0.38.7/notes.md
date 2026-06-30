# terraform-ls 编译笔记

## 基本信息

- 软件名: terraform-ls
- 版本: v0.38.7
- 类型: go 工具
- 编译日期: 2026-06-15

## 编译过程

### 编译方式

使用 go install 直接安装：
- Go 工具: `go install github.com/...@v0.38.7`
- Rust 工具: `cargo install terraform-ls`

### 验证

- 二进制文件: `~/go/bin/terraform-ls` 或 `~/.cargo/bin/terraform-ls`
- 功能验证: `terraform-ls --version` ✅

## 制品信息

- 制品包: `packaging/terraform-ls-v0.38.7-ohos-aarch64.tar.gz`
- 内容: `bin/terraform-ls`

## 备注

此软件通过 go install 直接安装成功，制品从已安装二进制打包创建。
