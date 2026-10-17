# atlantis 0.46.0 适配笔记

## 编译环境
- 构建系统: custom (Go build)
- 编译日期: 2026-08-11
- 编译器: Go 1.26.4 (linux/arm64，go.mod 要求 go 1.26.4)
- 状态: built

## 上游身份

- 平台库名: atlantis（与上游一致）
- 上游项目: runatlantis/atlantis（Terraform Pull Request Automation）
- 版本/tag: v0.46.0（2026-06-30 发布）
- 官方仓库: https://github.com/runatlantis/atlantis
- 源码: https://github.com/runatlantis/atlantis/archive/refs/tags/v0.46.0.tar.gz
- SHA256: 35ee65ebecd4c9999e9841aaa3e5bce626f292de6b4bcf22fd5c4599898f1178
- 许可证: Apache-2.0

## 编译步骤

atlantis 是纯 Go 应用（Terraform PR 自动化服务 + CLI），无 configure/make 流程，直接 `go build` 交叉编译：

```bash
# 关键：本机 HMDFS 无法执行未签名的静态 Go 工具链（E045），
# 需要下载 go1.26.4.linux-arm64.tar.gz 并用 binary-sign-tool 批量 ELF 签名
# 关键：TMPDIR 必须可写（/data/storage/el2/base/cache），Go linker 使用 mmap

GOROOT=<signed-go-root> \
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 \
GOFLAGS=-mod=mod GOPROXY=https://goproxy.cn,direct \
TMPDIR=/data/storage/el2/base/cache \
go build -trimpath -ldflags="-s -w" -o atlantis .

# 签名产物（鸿蒙 ELF 签名要求）
binary-sign-tool sign -inFile atlantis -outFile atlantis.signed -selfSign 1

# 验证
./atlantis version
# → atlantis dev (commit: none) (build date: unknown)，exit 0
```

## 上游测试

- 162 个 `*_test.go` 文件，43 个测试包
- 入口: `go test ./...`（make test / make test-all）
- e2e/ 测试需要 docker + 真实 VCS 环境，本机不可运行
- `go test ./...` 生成的测试二进制位于 Go build cache，无法预签名，
  本机 HMDFS 上执行报 permission denied（E045 已知平台限制）；
  已通过 `go test -c` + ELF 签名 + 手动运行测试二进制的方式在本机真实执行
  核心包（cmd/ 等）测试，结果见 reports/

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Go 工具链 exec Permission denied | 鸿蒙要求 ELF 签名（E045） | 下载 go1.26.4 后 binary-sign-tool 批量签名 67 个 ELF |
| 2 | proxy.golang.org 连接超时 | 网络受限 | GOPROXY=https://goproxy.cn,direct |
| 3 | /tmp 只读 | 鸿蒙平台 | TMPDIR=/data/storage/el2/base/cache |
| 4 | go test 测试二进制 permission denied | 测试二进制在 build cache 无法预签名 | go test -c 编译到独立目录后签名再运行 |
| 5 | TestAllFlagsDocumented 失败 | 测试需要 ../runatlantis.io/docs/server-configuration.md（源码目录上下文） | 从源码根目录运行测试可解析 |

## 依赖版本

- Go 1.26.4（go.mod 声明，纯 Go 无 C 依赖）
- Go module 依赖由 GOPROXY 拉取（go.sum 841 行，无 vendor）

## 验证结果

```bash
go build -o atlantis .        # 通过，产物 39.7MB arm64
./atlantis version            # atlantis dev (commit: none)，exit 0
go test -c ./cmd/ + 签名运行  # cmd 包 45 个测试用例，见 reports/
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Go 应用配方（source/build/package/package_info） |
| conandata.yml | 官方源码 URL + SHA256 |
| test_package/ | 消费者测试（atlantis version） |
| commands.json | 命令行工具声明（R38） |

## 注意事项

- 平台库名、上游项目名、Conan name 均为 `atlantis`，无名称差异
- 版本 `0.46.0` 与上游 tag `v0.46.0` 一致
- 归档路径 archives/a/atlantis/0.46.0/ 与预期一致
- 状态标记为 built（conan-verify 通过、未 upload）
---

**编译结束**: 2026-08-11 19:05
**最终状态**: built
