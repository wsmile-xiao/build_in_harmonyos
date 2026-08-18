# meek

> Tor 的抗封锁可插拔传输工具

## 简介

meek 是 Tor 项目的可插拔传输（Pluggable Transport）实现，通过将数据流编码为
HTTPS 请求/响应，经第三方服务器（如 CDN）中继，从而绕过网络封锁。

meek 包含两个组件：
- **meek-client**：客户端代理，在本地运行，与 Tor 客户端配合
- **meek-server**：服务端代理，部署在境外服务器上，与 CDN 配合

## OHOS 适配要点

- Go 项目使用 `go build` 直接编译，无需 configure/make
- `CGO_ENABLED=0` 实现纯 Go 静态链接（R26），无 C 库依赖
- `GOOS=linux` 映射 HarmonyOS（Go 不支持 ohos 作为 GOOS）
- `GOARCH=arm64` 映射 Conan `arch=armv8`

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| Go | >= 1.21 | 构建工具链（CI 环境提供） |

## 功能验证

```bash
# 验证 meek-client 可执行（预期输出 ENV-ERROR，退出码 1）
meek-client 2>/dev/null
# 输出: ENV-ERROR no TOR_PT_MANAGED_TRANSPORT_VER

# 验证 meek-server 可执行（预期输出 ENV-ERROR，退出码 1）
meek-server 2>/dev/null
# 输出: ENV-ERROR no TOR_PT_MANAGED_TRANSPORT_VER
```

## 参考

- [Tor Project](https://www.torproject.org)
- [meek 源码](https://gitlab.torproject.org/tpo/anti-censorship/pluggable-transports/meek)
