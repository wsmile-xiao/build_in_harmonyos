# newrelic 编译笔记

## 基本信息

- 软件名: newrelic
- 版本: v0.0.0-20260603111055
- 类型: go 工具
- 编译日期: 2026-06-15

## 编译过程

### 编译方式

使用 go install 直接安装：
- Go 工具: `go install github.com/...@v0.0.0-20260603111055`
- Rust 工具: `cargo install newrelic`

### 验证

- 二进制文件: `~/go/bin/newrelic` 或 `~/.cargo/bin/newrelic`
- 功能验证: `newrelic --version` ✅

## 制品信息

- 制品包: `packaging/newrelic-v0.0.0-20260603111055-ohos-aarch64.tar.gz`
- 内容: `bin/newrelic`

## 备注

此软件通过 go install 直接安装成功，制品从已安装二进制打包创建。
