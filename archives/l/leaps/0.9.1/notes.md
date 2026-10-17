# leaps 0.9.1 适配笔记

## 选型与版本核验

- 上游：Jeffail/leaps，`v0.9.1` tag（GitHub 官方 tag archive，sha256
  8335e2a939ac5928a05f71df4014529b5b0f2097152017d691a0fb6d5ae27be4，实测）
- 语言：**纯 Go**（73 个 .go，0 C/C++）；go.mod 要求 go 1.12
- 功能：协作式网页结对编程编辑器（operational transform 同步服务），main 包 `./cmd/leaps`

## 语言预检（R47）与任务元数据纠正

- 任务平台元数据 `lang=cpp` 与项目真实语言不符（纯 Go 项目）。
- 按 AGENTS.md 2026-09 实测口径（Go 可行，先例 cc-connect/1.4.1、flow-cli）与
  flow-cli（任务 lang=cpp、Go、done）先例，`lang-preflight --lang go` 通过
  （task=go, detected=go, 源统计 go:73/nodejs:21）。
- 历史：早前分支曾按 R47 判 `env_unsupported`（纯 Go 无 C API）——与
  2026-09-07 之后"Go 生态可行"的知识库口径冲突，本次按新口径真正编译交付。

## 编译环境

- 构建系统：go（官方发行版工具链自举）
- Go 工具链：go1.25.12.linux-arm64（golang.google.cn + dl.google.com 双源，
  sha256 8b5884ae…f7bd2，cc-connect/caddy 同款且 CI 已验证）
- Go 模块代理：goproxy.cn + GOSUMDB=sum.golang.google.cn（go.sum 校验）
- CGO_ENABLED=0：依赖树纯 Go
- 状态：built（conan-verify 八门禁通过；CI 未跑，未 upload）

## E549 ELF 签名（本机实测）

- Go 工具链树（bin/go、bin/gofmt、pkg/tool/*）全部 binary-sign-tool 自签名后才可执行
- `go test` 编译出的**测试二进制同样需签名**：用 `go test -exec <signer-wrapper>`
  包装器逐一对测试二进制签名后再执行（本机实测 53/53 通过的关键步骤）
- 最终 leaps 产物签名后交付 test_package

## E331/E523：link 输出必须走 el2 app-files

- Go linker 以 PROT_EXEC mmap 输出，hmdfs 拒绝（"mapping output file failed"）
- link 输出与 GOTMPDIR 放在 `/data/storage/el2/base/haps/entry/files/leaps-conan-go`
  （实测通过），构建完成拷回 build 目录再签名

## 上游测试（R51，本机全量实测）

- `go test ./...`（-exec 签名包装器）：**53 PASS / 0 FAIL / 0 SKIP**（12 个含测试包 + 3 个无测试文件包）
- `test/stories/*.js` 4 个 JS 故事文件需 node（设备无 node），不可运行，如实记录
- 消费者测试：test_package 执行 `leaps --help` 断言 "Usage: leaps"（R34）

## 目录结构（R38 commands.json 在软件级）

```
archives/l/leaps/
  ├── README.md / manifest.yaml / commands.json
  └── 0.9.1/
      ├── conanfile.py / conandata.yml / test_package/
      ├── manifest.yaml / notes.md
      └── reports/ (go-test-all.log, conan-verify-report.md, test-report.md)
```

## 待办

- CI 绿后 submit 升级终态；可评估后续版本启用 JS 客户端测试（需 node 生态）
---

**编译结束**: 2026-09-29 09:23
**最终状态**: built
