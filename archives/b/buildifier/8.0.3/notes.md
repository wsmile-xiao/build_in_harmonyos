# buildifier 8.0.3 — 编译适配笔记

## 编译信息

| 项目 | 内容 |
|------|------|
| 软件 | buildifier (Bazel BUILD file formatter) |
| 版本 | 8.0.3 |
| 上游源码 | https://codeload.github.com/bazelbuild/buildtools/tar.gz/refs/tags/v8.0.3 |
| 构建系统 | Go (自定义) |
| 编译器 | Go >= 1.23.8 (conanfile.py 自动下载 Go 1.23.8 作为 fallback) |
| 目标平台 | linux/arm64 (HarmonyOS) |

## 编译步骤

buildifier 是 bazelbuild/buildtools 仓库中的 Go 工具，用于格式化 Bazel BUILD 文件。

### Go 项目编译要点

1. **Go 版本**: conanfile.py 使用 Go >= 1.23.8，如系统未安装则自动下载 Go 1.23.8
2. **静态编译**: `CGO_ENABLED=0` 确保生成纯静态 ELF，无动态库依赖
3. **交叉编译参数**: `GOOS=linux GOARCH=arm64` (本平台为 native 编译)
4. **Go 代理**: `GOPROXY=https://goproxy.cn,direct` 使用国内镜像加速依赖下载
5. **Strip 符号**: `-ldflags="-s -w"` 去除调试信息和符号表，减小二进制体积
6. **版本注入**: `-ldflags="-X main.buildVersion=8.0.3 -X main.buildScmRevision=v8.0.3"` 将版本号写入二进制

### ELF 签名

所有 ELF 二进制必须通过 `binary-sign-tool` 签名才能在 HarmonyOS 上执行。
conanfile.py 自动处理 Go SDK 和 buildifier 产物的签名。

### 历史编译信息

历史编译使用 Go 1.26.3（手动安装），conanfile.py 改为自动下载 Go 1.23.8，
并自动处理 ELF 签名。Go 1.23.8 在 HarmonyOS 上验证可用。

## 功能验证

| 测试 | 结果 |
|------|------|
| `buildifier --version` | ✅ 显示 `buildifier version: 8.0.3, scm revision: v8.0.3` |
| `buildifier --mode=fix` | ✅ 正确格式化 BUILD 文件 |
| `buildifier --mode=check` | ✅ 检查模式正常 |
| `buildifier --lint=warn` | ✅ Lint 模式正常检测警告 |
| ELF `.codesign` section | ✅ 签名完整 |

## 注意事项

- **无 configure/make**: Go 项目不需要 configure 和 make，直接使用 `go build`
- **模块路径**: 源码模块为 `github.com/bazelbuild/buildtools`，buildifier 是子包 `./buildifier`
- **go.mod 要求**: Go 1.20+，与 Go 1.23.8 兼容
- **OHOS 链接问题**: Go linker 在 HMDFS 上无法 mmap 输出文件，需使用 `/data/storage/el2/base/haps/entry/files/` 作为工作目录
- **ELF 签名**: Go SDK 的所有二进制（go, gofmt, compile, link 等）都需要签名

**最终状态**: built (conan-adapted)
