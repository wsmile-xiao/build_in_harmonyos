# buildifier 8.0.3 — 编译适配笔记

## 编译信息

| 项目 | 内容 |
|------|------|
| 软件 | buildifier (Bazel BUILD file formatter) |
| 版本 | 8.0.3 |
| 上游源码 | https://github.com/bazelbuild/buildtools/archive/refs/tags/v8.0.3.tar.gz |
| 构建系统 | Go (自定义) |
| 编译器 | Go 1.26.3 (Go 1.26.0 已知 corrupted, 必须用 1.26.3) |
| 目标平台 | linux/arm64 (HarmonyOS) |

## 编译步骤

buildifier 是 bazelbuild/buildtools 仓库中的 Go 工具，用于格式化 Bazel BUILD 文件。

### Go 项目编译要点

1. **Go 版本选择**: Go 1.26.0 二进制在 HarmonyOS 上存在 corrupted 问题，必须使用 Go 1.26.3 (`/storage/Users/currentUser/usr/local/go1263/bin/go`)
2. **静态编译**: `CGO_ENABLED=0` 确保生成纯静态 ELF，无动态库依赖
3. **交叉编译参数**: `GOOS=linux GOARCH=arm64` (本平台为 native 编译)
4. **Go 代理**: `GOPROXY=https://goproxy.cn,direct` 使用国内镜像加速依赖下载
5. **Strip 符号**: `-ldflags="-s -w"` 去除调试信息和符号表，减小二进制体积
6. **版本注入**: `-ldflags="-X main.buildVersion=8.0.3 -X main.buildScmRevision=v8.0.3"` 将版本号写入二进制

### 编译命令

```bash
export GOROOT=/storage/Users/currentUser/usr/local/go1263
export PATH="$GOROOT/bin:$PATH"
export CGO_ENABLED=0 GOOS=linux GOARCH=arm64
export GOPROXY=https://goproxy.cn,direct
export TMPDIR=/data/storage/el2/base/cache

cd $BUILD_SRC_DIR
go build -ldflags="-s -w -X main.buildVersion=8.0.3 -X main.buildScmRevision=v8.0.3" \
  -o $TEST_PREFIX/$DEFAULT_PREFIX/bin/buildifier ./buildifier
```

### DESTDIR 模式

| 变量 | 路径 | 用途 |
|------|------|------|
| DEFAULT_PREFIX | ~/usr/local | 运行时安装路径 |
| TEST_PREFIX | ~/tmp/test-install-buildifier-8.0.3 | DESTDIR staging 目录 |

Go 项目没有标准 `make install DESTDIR=...` 机制，通过 `go build -o` 直接指定输出路径到 `$TEST_PREFIX/$DEFAULT_PREFIX/bin/buildifier`。

## ELF 签名

所有 ELF 二进制必须通过 `binary-sign-tool` 签名才能在 HarmonyOS 上执行：

```bash
/data/service/hnp/bin/binary-sign-tool sign -inFile buildifier -outFile buildifier.signed -selfSign 1
```

签名后检查 `.codesign` section 存在：
```bash
/data/service/hnp/bin/llvm-readelf -S buildifier | grep codesign
```

## 功能验证

| 测试 | 结果 |
|------|------|
| `buildifier --version` | ✅ 显示 `buildifier version: 8.0.3, scm revision: v8.0.3` |
| `buildifier --mode=fix` | ✅ 正确格式化 BUILD 文件 |
| `buildifier --mode=check` | ✅ 检查模式正常 |
| `buildifier --lint=warn` | ✅ Lint 模式正常检测警告 |
| ELF `.codesign` section | ✅ 签名完整 |

## 注意事项

- **Go 1.26.0 不可用**: 在 HarmonyOS 上 Go 1.26.0 二进制文件存在 corrupted 问题，必须使用 Go 1.26.3
- **无 configure/make**: Go 项目不需要 configure 和 make，直接使用 `go build`
- **模块路径**: 源码模块为 `github.com/bazelbuild/buildtools`，buildifier 是子包 `./buildifier`
- **go.mod 要求**: Go 1.20+，与 Go 1.26.3 兼容
- **下载问题**: GitHub 直连超时，需使用 ghfast.top 镜像下载源码包
- **Text file busy**: 更新正在运行的二进制时需先 `rm -f` 再复制

**编译开始**: 2026-06-01  
**最终状态**: ✅ 编译成功
---

**编译结束**: 2026-06-02 11:44
**最终状态**: built
