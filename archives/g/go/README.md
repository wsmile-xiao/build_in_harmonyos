# Go

## 简介

Go 是一种开源编程语言，由 Google 开发。它具有简洁的语法、高效的编译速度和强大的并发支持。Go 编译器可以生成静态链接的二进制文件，适合跨平台部署。

## OHOS 适配

- Go 使用自举编译（bootstrap），需要已签名的 Go 编译器作为起点
- Go 1.4 是最后一个完全用 C 编写的版本，可作为 bootstrap
- Go 生成的二进制有非标准 ELF 格式（SHT_STRTAB string table 未 null-terminated）
- **必须先用 strip 处理二进制使其符合标准 ELF 格式，然后再用 sign-elf 签名**
- 编译时设置 `CGO_ENABLED=0` 实现静态编译，避免动态链接库依赖
- 临时文件目录需设置为可写路径：`TMPDIR=/data/storage/el2/base/cache`

## 依赖

- Bootstrap Go 编译器（Go 1.4 或更高版本的已签名二进制）
- C 编译器（仅用于 Go 1.4 bootstrap 编译）

## 功能验证

```bash
go version
go env
go build -o hello hello.go && ./hello
```

## 参考

- 官网: https://go.dev
- 源码: https://go.dev/dl
- 文档: https://go.dev/doc