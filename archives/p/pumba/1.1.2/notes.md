# pumba 1.1.2 适配笔记

## 编译环境
- 构建系统: Go (Makefile)
- 编译日期: 2026-06-04
- 编译器: Go 1.26.0 (linux/arm64)
- 状态: built

## 编译步骤

### 1. 源码下载与解压
- 使用 ghfast.top 镜像从 GitHub 下载 pumba-master.tar.gz
- 解压到 ~/builds/pumba-1.1.2.work
- 版本: 1.1.2 (从 VERSION 文件读取)

### 2. Go 环境安装与配置
- 安装 Go 1.26.0 (从 USTC 镜像下载 go1.26.0.linux-arm64.tar.gz)
- 使用 ohc-run.py sign-elf 签名所有 Go 工具链:
  - go, gofmt (bin/)
  - compile, link, asm, cgo, cover, fix, vet, preprofile (pkg/tool/linux_arm64/)
- 设置环境变量:
  - PATH=$HOME/usr/local/go-1.26.0/bin:$PATH
  - GOPROXY=https://goproxy.cn,direct
  - GOSUMDB=sum.golang.google.cn
  - CGO_ENABLED=0
  - GOOS=linux
  - GOARCH=arm64

### 3. 依赖分析
- go.mod 指定 go 1.26
- 依赖包要求 Go >= 1.25.0 (golang.org/x/sync@v0.20.0, go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp@v0.68.0)
- 使用 Go 1.26.0 满足依赖要求

### 4. 模块依赖下载
- 执行 `go mod download` 成功下载所有依赖包
- 依赖包数量: 100+ 个模块
- 使用 goproxy.cn 镜像加速下载

### 5. 编译尝试
- 执行 `go build -v ./cmd`
- 编译成功通过所有 Go 包的编译阶段
- **链接阶段失败**: link 工具权限被拒绝

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 源码下载失败(GitHub SSL 证书问题) | 网络访问限制 | 使用 ghfast.top 镜像下载成功 |
| 2 | Go 1.22.0 版本过低 | 依赖包要求 Go >= 1.25.0 | 安装 Go 1.26.0 |
| 3 | Go 工具链未签名 | ELF 签名要求 | 使用 ohc-run.py sign-elf 签名所有工具 |
| 4 | Go link 工具权限被拒绝 | HMDFS SELinux MAC 策略限制 | 尝试设置 TMPDIR/GOCACHE、更换编译目录，均无效。结论：平台限制，需等待系统更新或使用其他环境 |

### 问题 4 详细分析

**错误信息**:
```
/storage/Users/currentUser/usr/local/go-1.26.0/pkg/tool/linux_arm64/link: mapping output file failed: permission denied
```

**尝试的解决方案**:
1. 设置 TMPDIR=$HOME/tmp (无效)
2. 设置 GOCACHE=$HOME/tmp/go-build-cache (无效)
3. 在不同目录编译 (无效)
4. 使用不同的输出路径 (无效)

**根本原因**: HMDFS 文件系统的 SELinux 强制访问控制(MAC)策略限制了 Go link 工具的某些操作(mmap、临时文件创建、文件映射)。这不是传统的文件权限问题(chmod 无法解决),而是内核级的 SELinux 上下文限制。

**结论**: 平台限制,无法在当前 HMDFS 环境下编译 Go 项目。

## 源码修改

无补丁。尝试修改 go.mod 文件(go 1.26 → go 1.22 → go 1.24 → go 1.26),但最终发现是平台限制问题,修改无效,不需要固化为补丁。

## 依赖版本

- Go: 1.26.0 (linux/arm64)
- GOPROXY: https://goproxy.cn,direct
- 关键依赖:
  - github.com/containerd/containerd/v2 v2.2.3
  - github.com/docker/docker v28.5.2+incompatible
  - github.com/urfave/cli v1.22.17
  - github.com/sirupsen/logrus v1.9.4
  - golang.org/x/sync v0.20.0

## 验证结果

```bash
cd ~/builds/pumba-1.1.2.work
export PATH=$HOME/usr/local/go-1.26.0/bin:$PATH
export GOPROXY=https://goproxy.cn,direct
export CGO_ENABLED=0
export GOOS=linux
export GOARCH=arm64
go build -v ./cmd

# 输出:
[100+ Go 包成功编译]
# github.com/alexei-led/pumba/cmd
/storage/Users/currentUser/usr/local/go-1.26.0/pkg/tool/linux_arm64/link: mapping output file failed: permission denied
```

## 交付物

无打包产物(编译失败)

## 注意事项

1. **Go 项目在 HMDFS 上受 SELinux 限制，无法编译**
   - 所有 Go 项目在当前 HMDFS 环境下都会遇到 link 工具权限问题
   - 建议在其他环境(非 HMDFS)编译 Go 项目

2. **E103 知识条目已记录此平台限制**
   - 错误模式: `link: mapping output file failed: permission denied`
   - 类似问题: E046 (chmod 不生效 SELinux 限制)

3. **Go 工具链签名必要性**
   - Go 工具链二进制文件必须通过 ELF 签名才能执行
   - 使用 `ohc-run.py sign-elf` 签名所有工具

4. **GOPROXY 配置建议**
   - 使用国内镜像 https://goproxy.cn,direct 加速依赖下载
   - 设置 GOSUMDB=sum.golang.google.cn

---

## 解决方案成功（2026-06-04 20:09）

### 问题解决

通过在 `/data/storage/el2/base/cache` 目录下编译，成功绕过了 HMDFS 文件系统的 SELinux 权限限制。

### 编译过程

1. 创建编译目录: `/data/storage/el2/base/cache/build-pumba`
2. 复制源码到 cache 目录
3. 设置环境变量:
   - TMPDIR=/data/storage/el2/base/cache/tmp
   - GOCACHE=/data/storage/el2/base/cache/tmp/go-cache
4. 执行编译: `go build -v -o pumba ./cmd`
5. 编译成功，生成 25M 静态链接二进制文件

### 产物信息

- **二进制大小**: 17M (strip 后)
- **文件类型**: ELF executable, 64-bit LSB arm64, static
- **签名**: ✅ 已签名
- **验证**: ✅ 可执行（pumba --version）

### 关键发现

**/data/storage/el2/base/cache 目录特性**:
- 该目录可能在不同的文件系统上（非 HMDFS）
- SELinux 策略更宽松，允许 Go link 工具正常工作
- 可作为 Go 项目的备选编译目录

### 最终状态

**状态**: built
**预编译包**: pumba-1.1.2-ohos-aarch64.tar.gz (17M)
**安装路径**: ~/usr/local/bin/pumba
---

**编译结束**: 2026-06-04 20:11
**最终状态**: built
