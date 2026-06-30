# atlas 1.2.0 编译笔记

## 基本信息
- 软件：atlas
- 版本：1.2.0
- 描述：Database toolkit for managing database schemas
- 主页：https://atlasgo.io/
- 许可证：Apache-2.0

## 编译环境
- 构建系统：Go
- 源码来源：https://github.com/ariga/atlas/archive/refs/tags/v1.2.0.tar.gz
- 编译日期：2026-05-28

## 编译过程

### 依赖处理
1. **Go 版本问题**：
   - 系统预装 Go 1.22.10（~/usr/local/go）
   - atlas go.mod 要求 Go 1.24.13（根目录）和 Go 1.25.0（cmd/atlas）
   - 依赖 golang.org/x/sys@v0.42.0 需要 Go >= 1.25
   - **解决方案**：手动下载 Go 1.25.10 到 ~/sdk/go1.25.10，签名所有二进制工具链

2. **Go 工具链签名**：
   - 需要签名 ~/sdk/go1.25.10/bin/go 和 pkg/tool/linux_arm64/* 下的所有工具
   - 包括：asm, cgo, compile, cover, link, preprofile, vet

### 编译命令
```bash
# 使用 Go 1.25.10
export GOROOT=~/sdk/go1.25.10
export PATH=$GOROOT/bin:$PATH
export GOPROXY=https://goproxy.cn,https://proxy.golang.org,direct

cd cmd/atlas
go build -ldflags="-s -w -X ariga.io/atlas/cmd/atlas/internal/cmdapi.version=v1.2.0" -o atlas .
```

### 编译结果
- 产物：atlas 可执行文件（36M）
- 类型：动态链接 ELF，链接到 /lib/ld-musl-aarch64.so.1
- 状态：stripped（已去除符号）

## 验证结果
```
$ atlas version
atlas community version v1.2.0
https://github.com/ariga/atlas/releases/tag/v1.2.0
```

## 预编译包
- 文件名：atlas-1.2.0-ohos-aarch64.tar.gz
- 大小：36M
- 内容：bin/atlas
- 路径：archives/a/atlas/1.2.0/packaging/

## 特殊说明
1. atlas 是 Go 项目，无 configure/make install 步骤
2. Go 1.25.10 需要手动下载并签名所有工具链二进制
3. 预编译包制作使用简化流程（手动打包）
4. 系统预装的 Go 1.22.10 无法编译此版本，必须使用 Go 1.25+

## 源码修改清单
| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
| 无 | 无需修改源码 | - | - |

---

**编译开始**: 2026-05-28 20:27
**编译结束**: 2026-05-28 20:44
**最终状态**: built