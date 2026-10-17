# tut 2.0.1 适配笔记

## 软件信息

- **软件名**: tut
- **版本**: 2.0.1
- **上游仓库**: https://github.com/RasmusLindroth/tut
- **标签**: 2.0.1（无 `v` 前缀，commit 33d7cd8cbf5f8048b49bf218a3c7aed2ab3d6346）
- **描述**: TUI for Mastodon with vim inspired keys（Go 编写的 Mastodon 终端客户端）
- **许可证**: MIT
- **构建系统**: Go modules（go.mod 声明 `go 1.18`，CGO-free）
- **产物**: 静态可执行文件 `tut`（`go build .`，模块根目录的 main.go）

## 源码信息

- **源码包**: `https://github.com/RasmusLindroth/tut/archive/refs/tags/2.0.1.tar.gz`
- **sha256**: `afa8c49036461a36c091d83ef51f9a3bbd938ee78f817c6467175699a989b863`
- **大小**: 235547 字节，解包 96 个文件（已实测）
- **压缩格式**: tar.gz

## 上游测试审计（R51 三步法）

解包 2.0.1 源码树并递归实测（2026-10-04）：

- `*_test.go` 文件数：0（全树无匹配）
- `func Test` 定义数：0（所有 `*.go` 无匹配）
- `tests/`、`testdata/`、`testing/` 目录：无
- `Makefile` / `check` / `test` 目标：无（仓库仅用 `go build` / `go install`，`.github/` 为发布流水线）

结论：上游确实零测试。`test_package/MANIFEST.yml` 已按守则同时写入
`upstream_tests_exist: false` 与非空 `upstream_test_audit`，测试标记使用
`status:"no_tests"`、`discovered:0`、`executed:0` 及具体 `reason`。

## 构建步骤（真机预检将在 HMBS 侧执行）

1. `get` 解包上游 tarball（`strip_root=True`）。
2. 解析 Go 工具链：优先复用 `PATH` 或 `/storage/Users/currentUser/sdk/` 下已签名 Go；
   否则自举 `go1.24.0.linux-arm64.tar.gz`（golang.google.cn 优先、dl.google.com 回退，
   SHA-256 校验），解到 ext2 缓存并用 `llvm-objcopy --remove-section .codesign` +
   `binary-sign-tool sign -selfSign 1` + `chmod 0o755` 逐个重签 `bin/` 与
   `pkg/tool/linux_arm64/` 下 ELF（tlsx 先例，E128/E077）。
3. 组装 Go 环境：`CGO_ENABLED=0`、`GOPROXY=https://goproxy.cn,direct`、
   `GOTOOLCHAIN=local`、`GOCACHE/GOTMPDIR/TMPDIR` 指向 ext2（E166）。
4. `go version` 探活 → `go mod download` → `go build -trimpath -ldflags=-s -ldflags=-w -o <ext2>/tut-bin .`
5. 对产出 `tut` 做同流程 ELF 签名后拷回 Conan `build_folder`，`package()` 装到 `bin/`。

上游 `go 1.18` 需求由自举的 `go1.24.0` 满足（向前兼容）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 真机无可用 Go（`go: inaccessible or not found`） | HMBS 仅保证 cmake/make/ninja/python3；便携 Go 无 `.codesign`，鸿蒙拒绝 execve（E128） | 复用 tlsx 的自举+批量签名流水线，缓存于 ext2 `go-bootstrap/go1.24.0/` |
| 2 | Go 链接器在 HMDFS 上 mmap 失败 | HMDFS 不支持链接器输出文件的 mmap（E166） | GOCACHE/GOTMPDIR/链接 `-o` 全部指向 ext2，构建完拷回 |
| 3 | 默认 GOPROXY 不可达 | `proxy.golang.org` 在真机网络不可达 | `GOPROXY=https://goproxy.cn,direct` |
| 4 | 上游零测试如何申报 | 无 `*_test.go`，不能编造通过率 | `MANIFEST.yml` 写 `upstream_tests_exist:false`+审计，标记 `no_tests`+`reason` |

## 源码修改

无。上游源码零改动，`patches` 为空。

## 依赖版本

- 构建期：Go 1.24.0（自举便携工具链；若真机挂载已签名 SDK Go 则直接复用）
- 其余 Go 依赖全部由 `go.mod`/`go.sum` 经 `GOPROXY` 拉取，无 Conan host 依赖

## 验证结果

等待 HMBS 真机预检（本轮不提交、不推送）。预期：

```bash
tut --help     # 打印 usage，非空
tut --version  # 打印版本号，含数字，非空
tut example-config  # 生成非空 config.example.toml
```

消费者 3 断言；上游 0 测试（`no_tests`，已审计）。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/tut` | 静态 Mastodon TUI 可执行文件（CGO disabled，已签名） |

## 注意事项

- 本机为 Windows（大小写不敏感文件系统），`archives/l/libXext` 与 `archives/l/libxext`
  在本机检出互相覆盖、`archives/g/gama` 含 `\r` 非法文件名无法检出，均为本机限制；
  与 `tut` 无关，真机（Linux）不受影响。本分支仅新增 `archives/t/tut/2.0.1/`，不触碰上述目录。
- `tut` 为交互式 TUI，需 Mastodon 账号与网络才能进入主界面；消费者测试仅覆盖
  无需网络的 `--help`/`--version`/`example-config` 路径，不做登录与时间线断言。
