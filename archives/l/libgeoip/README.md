# libgeoip

## 简介

MaxMind GeoIP Legacy C 库（geoip-api-c）：基于本地 .dat 数据库文件的 IP 地理定位查询库。注意 GeoIP2（libmaxminddb）是新一代替代品，属不同软件。

## 版本信息

- 版本: 1.6.12（2018-01 上游最终版，Legacy 线定格）
- 上游: https://github.com/maxmind/geoip-api-c
- 许可证: LGPL-2.1-or-later

## 编译产物

- libGeoIP.so / libGeoIP.a（IP 地理定位库）
- geoiplookup: IPv4/主机名查询工具
- geoiplookup6: IPv6 查询工具

## OHOS 适配

- 构建系统: autotools（tarball 无 configure，build() 内 autoreconf -fiv 引导，automake/libtool 走 tool_requires）
- 目标平台: OpenHarmony aarch64 (OHOS 6.0, clang 15, libc++)
- 零依赖：核心库无任何强制依赖（不用 zlib，.dat 读取走裸 stdio+mmap）
- 上游测试 2/2 PASS（test-geoip / test-geoip-invalid-file，make check）
- 详见 1.6.12/notes.md 获取适配详情

## 数据文件说明

GeoIP.dat 等数据库文件**不打包**（运行时用户自备，上游亦如此）。
查询时用 `geoiplookup -d <目录>` 指定数据库目录，或通过
`GeoIP_setup_custom_directory()` API 设置。

## 使用方法

```bash
geoiplookup -d /path/to/dat 8.8.8.8
geoiplookup6 -d /path/to/dat 2001:4860::8888
```

## Conan 使用

```bash
conan install --requires=libgeoip/1.6.12
```
