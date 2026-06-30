# Notes — podman-tui 1.9.0

## 编译信息

- **软件**: podman-tui 1.9.0
- **来源**: GitHub (containers/podman-tui v1.9.0)
- **日期**: 2026-06-04
- **状态**: 编译成功

## 编译方法

podman-tui 是一个 Go 语言项目（Podman 终端 UI），使用 vendor 目录管理依赖。

### Go 项目编译要点

1. Go 工具链: ~/usr/local/go (go1.25.4)
2. GOPROXY=https://goproxy.cn,direct
3. CGO_ENABLED=0（静态编译，无 C 依赖）
4. `-mod=vendor` 使用 vendor 目录
5. 构建标签: `exclude_graphdriver_btrfs containers_image_openpgp remote`
6. 编译命令: `go build -mod=vendor -o bin/podman-tui -tags "exclude_graphdriver_btrfs containers_image_openpgp remote"`

### DESTDIR 安装

- 安装到 `$TEST_PREFIX/$DEFAULT_PREFIX/bin/podman-tui`
- 静态二进制，约42MB
- ELF 签名后可正常运行

## 功能验证

- `podman-tui version` → `podman-tui v1.9.0` ✅

## make check

podman-tui 需要 podman daemon 运行才能进行功能性测试，无法在当前环境运行。单元测试需要 ginkgo CLI，对编译验证不是必需的。

---

**编译结束**: 2026-06-04 01:22 UTC
**最终状态**: published
---

**编译结束**: 2026-06-04 01:28
**最终状态**: built
