# whosthere 编译笔记

## 基本信息

- 软件名: whosthere
- 版本: v0.0.0-20260612222631
- 类型: go 工具
- 编译日期: 2026-06-15

## 编译过程

### 编译方式

使用 go install 直接安装：
- Go 工具: `go install github.com/...@v0.0.0-20260612222631`
- Rust 工具: `cargo install whosthere`

### 验证

- 二进制文件: `~/go/bin/whosthere` 或 `~/.cargo/bin/whosthere`
- 功能验证: `whosthere --version` ✅

## 制品信息

- 制品包: `packaging/whosthere-v0.0.0-20260612222631-ohos-aarch64.tar.gz`
- 内容: `bin/whosthere`

## 备注

此软件通过 go install 直接安装成功，制品从已安装二进制打包创建。
