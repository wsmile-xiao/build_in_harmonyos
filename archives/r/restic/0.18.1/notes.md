# restic 0.18.1 适配笔记

## 编译环境
- 构建系统: Go (go build)
- 编译日期: 2026-06-03
- 编译器: Go 1.24.4 (via goenv)
- 状态: built

## 编译步骤

1. **Go工具链安装**: 通过goenv安装Go 1.24.4（满足go.mod要求的go 1.23.0最低版本）
2. **Go工具链签名**: 所有Go工具链二进制（go, gofmt, compile, link等）需ELF签名才能在鸿蒙执行
3. **设置goenv本地版本**: `goenv local 1.24.4` 覆盖go.mod中的1.23.0版本要求
4. **编译命令**: `go build -tags release -ldflags="-s -w" -o restic ./cmd/restic`
   - CGO_ENABLED=0：静态编译，无C依赖
   - GOPROXY=https://goproxy.cn,direct：使用国内代理加速下载
   - -tags release：启用release构建标签
   - -ldflags="-s -w"：strip符号和调试信息
5. **ELF签名**: `binary-sign-tool sign -selfSign 1 -inFile restic -outFile restic -keyAlias oh-key-v1`
6. **安装**: cp到DESTDIR ($TEST_PREFIX/$DEFAULT_PREFIX/bin/) 和本地 ($DEFAULT_PREFIX/bin/)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Python SSL import错误 | _ssl模块找不到BIO_s_file符号 | 设置LD_LIBRARY_PATH包含harmonybrew/lib |
| 2 | GitHub下载超时 | 网络连接不稳定 | 使用GitHub archive URL + 手动下载完整tar.gz替换缓存 |
| 3 | goen强制go.mod版本 | go.mod要求1.23.0但未安装 | `goenv local 1.24.4` 设置本地覆盖 |
| 4 | Go工具链permission denied | Go二进制未ELF签名 | 用binary-sign-tool签名所有Go工具链二进制 |
| 5 | build系统误判为autotools | 脚本从URL猜测build_system | 手动使用Go build命令编译（模式B） |

## 源码修改

无补丁。源码未做任何修改，直接使用go build编译。
仅添加了.go-version文件（goenv local 1.24.4设置）。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| Go | 1.24.4 | via goenv预编译包 |
| restic go.mod | go 1.23.0最低要求 | 1.24.4满足要求 |

## 验证结果

```bash
$ restic version
restic 0.18.1 compiled with go1.24.4 on linux/arm64
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| restic-0.18.1-ohos-aarch64.tar.gz | ~40MB | 预编译包 |

## 注意事项

1. Go项目编译需先签名Go工具链所有二进制（go, compile, link, asm等），否则permission denied
2. goenv会读取go.mod中的go版本指令，需设置local override
3. CGO_ENABLED=0是Go项目静态编译的标准做法，避免动态链接C库
---

**编译结束**: 2026-06-04 14:42
**最终状态**: built
