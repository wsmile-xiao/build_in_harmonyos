# minio latest 编译笔记

## 编译信息
- **编译日期**: 2026-05-29
- **编译器**: go1.26.0 linux/arm64
- **平台**: HarmonyOS (OpenHarmony)
- **架构**: aarch64
- **版本**: latest (DEVELOPMENT.GOGET)

## 编译过程

### 1. Go 编译环境准备
系统中已有的 Go 编译器：
- ~/usr/local/go/bin/go (使用此版本)

**注意**: Go 编译器需要 ELF 签名才能在鸿蒙上执行。系统中已有的 Go 编译器已经签名。

### 2. 环境变量设置
```bash
export TMPDIR=/data/storage/el2/base/cache
export GOPROXY=https://goproxy.cn,direct
export PATH=/storage/Users/currentUser/usr/local/go/bin:$PATH
export GOCACHE=$TMPDIR/go-cache
export GOTMPDIR=$TMPDIR/go-tmp
export CGO_ENABLED=0
```

### 3. 源码获取
```bash
cd ~/tmp/builds/minio-latest.work
git clone --depth 1 https://github.com/minio/minio.git .
```

### 4. 编译命令
由于 minio 的 Makefile checkdeps.sh 不支持 HarmonyOS，直接使用 go build：
```bash
go build -v -o minio .
```

编译成功，生成二进制文件: `minio` (134M)

### 5. Strip 和 ELF 签名
```bash
cp minio minio.stripped
strip minio.stripped
python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf minio.stripped
```

Strip 后文件大小: 99M

### 6. 功能验证
```bash
./minio.stripped --version
# 输出: minio version DEVELOPMENT.GOGET (commit-id=DEVELOPMENT.GOGET)
# Runtime: go1.26.0 linux/arm64
# License: GNU AGPLv3
```

## 已知限制

1. **HMDFS 限制**: Go 链接器在 HMDFS 文件系统上有权限问题
2. **Makefile checks 失败**: checkdeps.sh 不识别 HarmonyOS，需要跳过检查
3. **版本号**: 通过 `go build` 编译，版本号显示为 DEVELOPMENT.GOGET

## 编译依赖

Go 自动下载以下主要依赖（通过 GOPROXY）:
- github.com/minio/minio-go/v7
- github.com/minio/madmin-go/v3
- github.com/minio/pkg/v3
- cloud.google.com/go/storage
- github.com/elastic/go-elasticsearch/v7
- google.golang.org/grpc
- go.etcd.io/etcd/client/v3
- github.com/fraugster/parquet-go
- 等其他依赖

## 参考

- Go 项目编译参考: archives/n/nats-server/v2.12.6/notes.md
- E081: Go 编译器无法在鸿蒙执行（需要 ELF 签名）

---

## 编译结束

**编译完成时间**: 2026-05-29 16:08

**最终状态**: ✅ built (编译成功)

**编译产物**:
- 二进制文件: minio (99M, stripped)
- 预编译包: minio-latest-ohos-aarch64.tar.gz

**质量门禁**:
- ✅ G0: 干净构建验证通过（无补丁）
- ✅ G1: 二进制完整性通过
- ✅ G2: 功能可用性通过
- ✅ G3: 可移植性通过（静态编译，已签名）
- ✅ G4: 档案完整性通过

**归档路径**: `/storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent/archives/m/minio/latest`

---
*编译者: OpenDesk Compile Agent*
*日期: 2026-05-29*