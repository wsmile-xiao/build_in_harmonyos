# Cloud Foundry CLI

## 简介

Cloud Foundry CLI（cf 命令）是 Cloud Foundry 平台的官方命令行工具，用于部署、管理和监控云应用。它支持应用部署、服务绑定、路由管理等核心功能。

## OHOS 适配

- CF CLI v8.18.3 使用 Go 语言编写，需要 Go >= 1.25.0 编译
- 使用 `CGO_ENABLED=0` 实现静态编译，无动态链接库依赖
- Go 编译的二进制需要 ELF 签名才能在 OpenHarmony 上执行
- 补丁: go.mod 版本指令从 1.26.2 降至 1.25.0 以匹配可用 Go 工具链
- 版本号通过 ldflags -X 注入: `code.cloudfoundry.org/cli/v8/version.binaryVersion`
- Go linker 在 HMDFS 上无法 mmap 输出文件，需输出到 ext4 可写路径

## 依赖

- Go >= 1.25.0（编译器，非 Conan 依赖）

## 功能验证

```bash
cf --version
cf help
cf apps
```

## 参考

- 官网: https://cloudfoundry.org
- 源码: https://github.com/cloudfoundry/cli
- 文档: https://docs.cloudfoundry.org/cf-cli
