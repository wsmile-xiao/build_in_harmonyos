# cloud-sql-proxy

Google Cloud SQL Auth Proxy — 代理工具，用于安全连接 Google Cloud SQL 数据库实例。

## 版本列表

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.38.0 | built | 2026-08-06 |

## 说明

Cloud SQL Auth Proxy 是 Google Cloud 提供的工具，用于建立到 Cloud SQL 实例的安全连接，无需配置 SSL 或管理 IP 白名单。

## 编译特点

- Go 项目，使用 CGO_ENABLED=0 静态编译
- 需要 Go >= 1.25.7（go.mod 要求），使用 Go 1.26.3 编译
- 主包路径: cmd/cloud_sql_proxy
- 版本注入 ldflag: `-X github.com/GoogleCloudPlatform/cloudsql-proxy/proxy/util.versionString=VERSION`
- Conan 配方自动下载 Go 1.26.3 SDK（golang.google.cn + dl.google.com fallback）
- OHOS 平台 ELF 签名（binary-sign-tool）
