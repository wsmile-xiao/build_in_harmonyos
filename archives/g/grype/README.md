# grype

Grype 是一个容器镜像漏洞扫描器，由 Anchore 开发。

## 描述

Grype 可以扫描容器镜像和文件系统中的已知漏洞（CVE），支持 Docker 镜像、OCI 镜像和本地目录扫描。它与 Syft（SBT 工具）配合使用，可以生成软件物料清单（SBOM）并进行漏洞匹配。

## 已编译版本
- 0.112.0 (2026-05-26) — 预编译二进制

## 依赖
- 无额外依赖（预编译二进制方案）

## 特性
- 容器镜像漏洞扫描
- OCI/Docker 镜像支持
- 本地文件系统扫描
- 多种输出格式（table, json, sarif）
- 漏洞数据库自动更新

## 使用方法
```bash
# 扫描容器镜像
grype <image>

# 扫描本地目录
grype dir:<path>

# 查看版本
grype version
```

## 注意事项
- Go 语言项目在 HMDFS 上无法源码编译，使用官方预编译二进制 + ohc sign-elf 签名部署