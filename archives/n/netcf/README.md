# netcf

## 简介

netcf 是一个网络配置抽象库，提供跨平台的网络接口配置管理 API。它使用 augeas 解析和修改网络配置文件，支持多种 Linux 发行版的网络配置格式。

## 主要功能

- **网络接口管理**: 列举、查询、配置网络接口
- **跨平台抽象**: 统一的 API 接口，支持不同 Linux 发行版
- **配置文件解析**: 基于 augeas 的配置文件读写
- **XML 描述**: 使用 XML 描述网络配置，便于集成

## 编译信息

| 项目 | 值 |
|------|-----|
| 版本 | 0.1.7 |
| 状态 | published |
| 构建系统 | autotools |
| 构建日期 | 2026-06-09 |

## 鸿蒙平台适配

### 关键修复

1. **sockaddr_storage 重定义**: 创建 `linux/socket.h` wrapper 避免 SDK 与 musl libc 冲突
2. **NETCF_LIBDEPS 构建**: 修复 Makefile 中 -L 参数被当作目标的问题
3. **ELF 签名**: 所有动态库需签名才能在 HarmonyOS 上运行
4. **augeas 路径映射**: 修改 transform 配置支持自定义 root 目录
5. **配置文件创建**: 创建 `ifcfg-*` 文件支持网络接口检测

### 使用说明

```bash
# 需使用 -r 参数指定 root 目录
ncftool -r /storage/Users/currentUser

# API 调用
ncf_init(&ncf, "/storage/Users/currentUser");
```

### 功能测试结果

| 测试项 | 结果 |
|--------|------|
| ncf_init/close | ✅ PASS |
| ncf_num_of_interfaces | ✅ PASS |
| ncf_list_interfaces | ✅ PASS |
| ncf_lookup_by_name | ✅ PASS |
| ncftool list | ✅ PASS |

## 依赖关系

- augeas 1.14.1
- libxslt 1.1.39
- libnl-1 1.1
- readline 8.3

## 已编译版本

- **0.1.7**: published (2026-06-09)

## 相关链接

- 官方网站: https://pagure.io/netcf/
- 源码下载: https://releases.pagure.org/netcf/