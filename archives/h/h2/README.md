# H2 Database Engine

## 软件介绍

H2 是一个用 Java 编写的关系数据库管理系统。它具有以下特点：

- **嵌入式数据库**：可以直接嵌入到 Java 应用中
- **内存数据库**：支持内存模式，适合测试和临时数据处理
- **兼容性强**：支持标准 SQL，兼容 PostgreSQL、MySQL 等数据库的部分语法
- **高性能**：小巧快速，适合中小规模应用

## 依赖

- **Java**: OpenJDK 17.0.13 (BiSheng) 或更高版本
- **Maven**: 3.6+ (用于构建)

## OpenHarmony 适配要点

1. **HMDFS 权限问题**：Maven 本地仓库需设置为 `/data/storage/el2/base/cache/m2-repo`，避免 HMDFS 文件系统的 hmmac 权限限制
2. **镜像加速**：配置阿里云 Maven 镜像加速依赖下载
3. **无需 ELF 签名**：Java jar 文件不需要 ELF 签名，可直接运行

## 使用方法

```bash
# 启动 H2 Shell
h2

# 或直接使用 jar 文件
java -cp ~/usr/local/share/h2/h2-2.2.224.jar org.h2.tools.Shell

# 启动 Web Console
java -cp ~/usr/local/share/h2/h2-2.2.224.jar org.h2.tools.Console
```

## 版本记录

- **2.2.224** (2026-06-09): 编译成功，已发布