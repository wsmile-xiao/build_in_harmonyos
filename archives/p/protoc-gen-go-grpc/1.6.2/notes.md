# protoc-gen-go-grpc 1.6.2 编译笔记

## 软件概述
- **软件名**: protoc-gen-go-grpc
- **版本**: 1.6.2
- **描述**: Protoc plugin that generates Go gRPC service code
- **主页**: https://github.com/grpc/grpc-go
- **License**: Apache-2.0
- **构建系统**: Go (google.golang.org/grpc/cmd/protoc-gen-go-grpc)

## 编译信息

### 源码获取
- **URL**: https://github.com/grpc/grpc-go/archive/refs/tags/cmd/protoc-gen-go-grpc/v1.6.2.tar.gz
- **说明**: protoc-gen-go-grpc 是 grpc-go 仓库的子模块，位于 `cmd/protoc-gen-go-grpc/` 目录下
- **Homebrew Formula**: Homebrew #712, 4551 installs

### 编译环境
- **Go 版本**: 1.26.3 (避免 1.26.0 corrupted runtime source 问题)
- **GOROOT**: /storage/Users/currentUser/usr/local/go1263
- **编译参数**: CGO_ENABLED=0 GOOS=linux GOARCH=arm64
- **GOPROXY**: https://goproxy.cn,direct
- **ldflags**: -s -w (strip symbols + disable DWARF)
- **编译目录**: cmd/protoc-gen-go-grpc/ (子模块独立 go.mod)
- **输出位置**: /data/storage/el2/base/cache/ (避免 HMDFS 上 Go linker mmap 失败)

### 编译步骤
1. 下载 grpc-go 仓库（tag: cmd/protoc-gen-go-grpc/v1.6.2）
2. 解压到 work 目录
3. cd cmd/protoc-gen-go-grpc/
4. `CGO_ENABLED=0 GOOS=linux GOARCH=arm64 GOPROXY=https://goproxy.cn,direct go build -ldflags="-s -w" -o protoc-gen-go-grpc .`
5. install 到 $DEFAULT_PREFIX/bin/ 和 DESTDIR staging

### 关键适配
- **静态编译**: CGO_ENABLED=0（Go 项目在鸿蒙上使用纯 Go 静态编译，避免动态依赖）
- **Go 版本**: 使用 1.26.3（1.26.0 有 corrupted runtime source 问题）
- **HMDFS 限制**: Go linker mmap 在 HMDFS 上失败，输出到 /data/storage/el2/base/cache/
- **无需 configure/make**: Go 项目直接 `go build`

### 验证结果
- `protoc-gen-go-grpc --version` → 输出 `protoc-gen-go-grpc 1.6.2`
- ELF 签名: .codesign section 存在 ✅
- 文件类型: ELF executable, 64-bit LSB arm64, static ✅
- 文件大小: 6.4M (strip 后)

### 产物清单
- bin/protoc-gen-go-grpc (单一二进制文件)

### 依赖
- **构建依赖**: Go >= 1.25.0
- **运行依赖**: 无（静态编译，零动态依赖）
- **Homebrew 依赖**: go (build), protobuf (runtime 但非链接依赖)

---

**编译开始**: 2026-06-01
**编译结束**: 2026-06-01
**最终状态**: published
---

**编译结束**: 2026-06-01 18:58
**最终状态**: published
