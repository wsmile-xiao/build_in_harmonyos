# MinIO

MinIO 是一个高性能的开源对象存储服务器，完全兼容 Amazon S3 API。

## 软件信息

- **类别**: Part2 #82 (存储服务)
- **安装量**: 2145
- **License**: GNU AGPLv3
- **构建系统**: Go
- **官方站点**: https://min.io
- **GitHub**: https://github.com/minio/minio

## 描述

MinIO 是高性能、S3 兼容的对象存储解决方案，设计用于 AI/ML、数据分析和大规模数据工作负载。

### 主要特性

- S3 API 兼容 - 与现有 S3 工具无缝集成
- 高性能 - 适用于 demanding 存储工作负载
- AI & Analytics 优化 - 为大规模数据管道优化
- 分布式架构 - 支持分布式部署和高可用性

## 编译版本

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| latest | built | 2026-05-29 | 开发版本 |

## 编译说明

MinIO 是一个 Go 项目，使用 `go build` 编译。需要：
- Go 1.16+ (推荐 Go 1.26+)
- GOPROXY 设置 (推荐 https://goproxy.cn)
- CGO_ENABLED=0 (静态编译)

## 依赖

- Go 编译器 (已签名)
- 网络连接 (下载依赖)

## 使用示例

```bash
# 启动 minio 服务器
minio server /data --console-address ":9001"

# 访问控制台
# http://localhost:9001
```

## 已知问题

1. Makefile checkdeps.sh 不支持 HarmonyOS，需要跳过检查
2. 版本号显示为 DEVELOPMENT.GOGET (开发版本)

---
*归档维护者: OpenDesk Compile Agent*