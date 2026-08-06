# cloud-sql-proxy 1.38.0 适配笔记

## 编译环境
- 构建系统: go
- 编译日期: 2026-08-06
- 编译器: Go 1.26.3 (auto-downloaded SDK)
- 状态: built

## 编译步骤

cloud-sql-proxy是Google Cloud SQL Auth Proxy的Go工具项目。由于go.mod要求Go >= 1.25.7，使用Go 1.26.3编译。

```bash
# 设置Go 1.26.3环境
export PATH=~/usr/local/go1263/bin:$PATH
export GOROOT=~/usr/local/go1263
export GOPROXY=https://goproxy.cn,direct
export TMPDIR=/data/storage/el2/base/cache

# 静态编译（CGO_ENABLED=0避免PIE/DYN签名损坏TLS header）
cd $BUILD_SRC_DIR
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build \
  -ldflags="-s -w -X github.com/GoogleCloudPlatform/cloudsql-proxy/proxy/util.versionString=1.38.0" \
  -o $TMPDIR/cloud-sql-proxy ./cmd/cloud_sql_proxy/

# 安装
install -m 755 $TMPDIR/cloud-sql-proxy $DEFAULT_PREFIX/bin/cloud-sql-proxy
install -m 755 $TMPDIR/cloud-sql-proxy $TEST_PREFIX/$DEFAULT_PREFIX/bin/cloud-sql-proxy

# ELF签名
python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf $DEFAULT_PREFIX/bin/cloud-sql-proxy
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build无法下载GitHub源码 | SSL证书验证失败 | 设置SSL_CERT_FILE=/storage/Users/currentUser/usr/local/ssl/cert.pem，使用curl -kL下载 |
| 2 | go.mod要求Go >= 1.25.7 | cloud-sql-proxy v1.38.0依赖新版Go | 使用Go 1.26.3（避免Go 1.26.0的corrupted runtime source） |
| 3 | go install找不到主包 | Go模块名是cloudsql-proxy（无连字符），主包路径是cmd/cloud_sql_proxy（下划线） | 正确路径: github.com/GoogleCloudPlatform/cloudsql-proxy/cmd/cloud_sql_proxy |
| 4 | ldflag -X main.version失败 | version变量是flag.Bool（*bool类型），不是string | 使用正确的ldflag: -X github.com/GoogleCloudPlatform/cloudsql-proxy/proxy/util.versionString=1.38.0 |

## 依赖版本

| 依赖 | 版本 |
|------|------|
| Go | 1.26.3 |

## 验证结果

```bash
$ cloud-sql-proxy --version
Cloud SQL Auth proxy: 1.38.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| cloud-sql-proxy | 16.4MB | 静态编译ELF arm64可执行文件 |

## 注意事项

- Go项目模块名可能与GitHub仓库名不同（cloudsql-proxy vs cloud-sql-proxy）
- Go项目主包通常不在根目录，需确认cmd/子目录
- ldflag注入版本字符串需确认正确的包路径和变量名
- Go 1.26.0有corrupted runtime source问题，必须用1.26.3
---

**编译结束**: 2026-08-06 03:43
**最终状态**: built
