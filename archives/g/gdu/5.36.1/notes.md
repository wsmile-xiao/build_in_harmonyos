# gdu 5.36.1 适配笔记

## 编译环境
- 构建系统: custom (Go 语言项目)
- 编译日期: 2026-08-06
- 编译器: Go 1.26.5 (via Harmonybrew), clang/clang++ (辅助)
- 状态: built (conan-verify 通过)

## 编译步骤

1. 安装 Go 编译器: brew install go (Harmonybrew, Go 1.26.5)
2. 编译 gdu 二进制:
   ```bash
   TMPDIR=/data/storage/el2/base/haps/entry/files
   GOCACHE=/data/storage/el2/base/haps/entry/files/go-cache
   GOPATH=/data/storage/el2/base/haps/entry/files/go-path
   GOPROXY=https://goproxy.cn,direct
   CGO_ENABLED=0 go build -trimpath -mod=mod -modcacherw \
     -ldflags="-s -w -extldflags '-static' \
               -X 'github.com/dundee/gdu/v5/build.Version=v5.36.1' \
               -X 'github.com/dundee/gdu/v5/build.Time=2026-08-06' \
               -X 'github.com/dundee/gdu/v5/build.User=ohos-builder'" \
     -o /data/storage/el2/base/haps/entry/files/gdu-output/gdu \
     github.com/dundee/gdu/v5/cmd/gdu
   ```
   注意：输出目录和 TMPDIR 必须在支持 mmap 的 hmfs 文件系统上
3. 复制到 staging: cp → $TEST_PREFIX/bin/gdu
4. 验证: gdu --version 输出正确

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Go linker "mapping output file failed: permission denied" | 鸿蒙 tmpfs 不支持 mmap ACCESS_WRITE，Go linker 依赖 mmap 写输出 | 将输出目录(-o)和 TMPDIR 设置到 hmfs 文件系统(/data/storage/el2/) |
| 2 | PIE 二进制 ELF 签名后 segfault | ELF 签名破坏了 NOBITS section(.bss/.noptrbss)的偏移量 | 使用非 PIE 静态二进制(CGO_ENABLED=0, 不加 -buildmode=pie) |
| 3 | go test 无法运行 | 测试二进制需要 ELF 签名才能在鸿蒙执行 | go test -c → 手动签名 → 执行 |
| 4 | TestGetFlagWithSymlink 失败 | /tmp 为 erofs 只读(E002) | 平台限制，记录为已知问题 |
| 5 | TestItemFromDirParallelWithErr 失败 | SELinux 限制 chmod 不生效(E046) | 平台限制，记录为已知问题 |
| 6 | Go module 下载失败 | proxy.golang.org 不可达(HarmonyOS 网络限制) | 配置 GOPROXY=https://goproxy.cn,direct |

## 源码修改

无源码修改。gdu 为纯 Go 项目，CGO_ENABLED=0 编译无需修改源码。

## 依赖版本

- Go 1.26.5 (via Harmonybrew)
- gdu 依赖通过 go.mod 管理，编译时自动下载

## 验证结果

```bash
$ gdu --version
Version:    v5.36.1
Built time:  2026-08-06
Built user:  ohos-builder
```

## Conan 配方

- conanfile.py: Go 自定义构建系统配方
- conandata.yml: 源码 URL + SHA256
- test_package/: 可执行文件 smoke test (gdu --version)
- commands.json: CLI 工具声明 (R38)
- package_type: application

## 注意事项

- Go linker 必须在支持 mmap 的文件系统上操作
- 不要使用 -buildmode=pie（与 ELF 签名冲突）
- GOPROXY 必须配置为可达的镜像 (goproxy.cn)
- Harmonybrew 安装的 Go 路径: /storage/Users/currentUser/.harmonybrew/bin/go
---

**编译结束**: 2026-08-06 12:45
**最终状态**: built (conan-verify 通过)
