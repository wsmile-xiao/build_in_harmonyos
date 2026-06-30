# nats-server v2.12.6 编译笔记

## 编译信息
- **编译日期**: 2026-05-29
- **编译器**: go1.25.10 linux/arm64
- **平台**: HarmonyOS (OpenHarmony)
- **架构**: aarch64

## 编译过程

### 1. Go 编译环境准备
系统中已有的 Go 编译器：
- ~/sdk/go1.25.10/bin/go (使用此版本)
- ~/go-1.26.1/bin/go
- ~/usr/local/go/bin/go

**注意**: Go 编译器需要 ELF 签名才能在鸿蒙上执行。系统中已有的 Go 编译器已经签名。

### 2. 编译命令
```bash
export TMPDIR=/data/storage/el2/base/cache
export GOPROXY=https://goproxy.cn,direct
export PATH=/storage/Users/currentUser/sdk/go1.25.10/bin:$PATH
export GOCACHE=$TMPDIR/go-cache
export GOTMPDIR=$TMPDIR/go-tmp
export CGO_ENABLED=0
export GOBIN=$TMPDIR/nats-server-build/bin

cd $TMPDIR/nats-server-build
go mod init nats-server-build
go install github.com/nats-io/nats-server/v2@v2.12.6
```

### 3. 依赖下载
Go 自动下载以下依赖：
- github.com/minio/highwayhash v1.0.4-0.20251030100505-070ab1a87a76
- github.com/nats-io/jwt/v2 v2.8.1
- github.com/nats-io/nkeys v0.4.15
- github.com/antithesishq/antithesis-sdk-go v0.6.0-default-no-op
- github.com/klauspost/compress v1.18.4
- golang.org/x/crypto v0.49.0
- github.com/nats-io/nuid v1.0.1
- golang.org/x/time v0.15.0
- golang.org/x/sys v0.42.0

### 4. 编译结果
- 编译成功，生成二进制文件: `$TMPDIR/nats-server-build/bin/nats-server`
- 文件大小: 20M

### 5. ELF 签名
nats-server 二进制文件需要 ELF 签名才能在鸿蒙上执行：
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py sign-elf $TMPDIR/nats-server-build/bin/nats-server
```

签名成功后，二进制可正常执行。

### 6. 功能验证
```bash
./nats-server --version
# 输出: nats-server: v2.12.6
```

## 已知限制

1. **HMDFS 限制**: Go 链接器在 HMDFS 文件系统上有权限问题（参考 kustomize 编译笔记）
2. **首次编译成功**: Go 项目首次编译通常成功，但重新编译注入版本号可能失败
3. **版本号**: 通过 `go install` 安装，版本号正确显示为 v2.12.6

## 参考

- Go 项目编译参考: archives/k/kustomize/5.8.1/notes.md
- E081: Go 编译器无法在鸿蒙执行（需要 ELF 签名）

---

## 编译结束

**编译完成时间**: 2026-05-29 15:47

**最终状态**: ✅ built (编译成功)

**编译产物**:
- 二进制文件: nats-server (14M, stripped)
- 预编译包: nats-server-v2.12.6-ohos-aarch64.tar.gz (14M)

**质量门禁**:
- ✅ G1: 二进制完整性通过
- ✅ G2: 功能可用性通过
- ✅ G3: 可移植性通过（静态编译，已签名）
- ✅ G4: 档案完整性通过

**归档路径**: `/storage/Users/currentUser/.opendesk/apps/skills/resources/openharmony-compile-agent/archives/n/nats-server/v2.12.6`

---
*编译者: OpenDesk Compile Agent*
*日期: 2026-05-29*