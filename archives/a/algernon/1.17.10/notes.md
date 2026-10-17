# algernon 1.17.10 HarmonyOS PC 适配笔记

## 编译环境
- 构建系统: go (Go modules, vendor 目录随源码分发)
- 编译日期: 2026-08-10
- 编译器: N/A (纯 Go, CGO_ENABLED=0)
- 状态: built

## 编译步骤

1. 下载上游官方 tag 源码包 `v1.17.10.tar.gz`（GitHub），SHA256 校验。
2. 解压后确认 `go.mod` 要求 go 1.26，vendor/ 目录包含全部依赖。
3. 使用本机/引导 Go 1.26.x 工具链（OHOS worker 无 go 时从阿里云镜像下载 go1.26.3，sha256 校验）。
4. 配方 build() 内先执行 `go test -mod=vendor ./...` 运行全部上游 Go 测试（OHOS 上通过 -exec wrapper 对测试二进制自签名）。
5. `go build -mod=vendor -trimpath -ldflags '-s -w' -buildvcs=false -o algernon .`
6. 对最终二进制调用 binary-sign-tool 自签名，OHOS 才能执行。
7. package 打包 bin/algernon + LICENSE + README.md。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Go 链接器在 HMDFS 下 mmap 失败 | 链接器输出写入 Conan build 目录受限 | 使用外部 hmfs work root（/data/storage/el2/base/cache）存放 GOCACHE/GOMODCACHE/GOPATH/TMPDIR 与链接输出，再拷贝回 build bin |
| 2 | OHOS 拒绝执行未签名 ELF | 平台安全要求 | go test -exec wrapper 自签名测试二进制；最终二进制用 binary-sign-tool -selfSign 1 签名 |
| 3 | 本机无 go 命令 | OHOS worker 未预装 Go | 配方自动查找常见 go 路径，否则引导下载 sha256 校验的 go1.26.3 工具链 |

## 源码修改

无补丁。未修改任何上游源码或测试文件。

## 依赖版本

- Go 工具链: go1.26.3（阿里云镜像，linux-arm64 sha256 9d89a3ea…）
- 上游 vendor 依赖随源码包提供，无需外部 conan 依赖。

## 验证结果

- `go test -mod=vendor ./...`：26 个 *_test.go 文件、118 个 func Test 用例（结果见最终日志）。
- 消费者测试 test_algernon.py：`algernon --version` 输出 "Algernon 1.17.10"；临时端口启动服务并 HTTP GET / 成功。

## 注意事项

- 任务页 C++ 标签不准确：algernon 是纯 Go 项目（BSD-3-Clause）。
- regtest/ 目录需要外部 vegeta 工具，不属于 go test 套件，未纳入统计。
---

**编译结束**: 2026-08-11 07:59
**最终状态**: built
