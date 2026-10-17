# codex-probe

Codex 凭证与诊断命令行工具 — 纯 Go 编写的单文件 CLI，把 Codex 令牌登录、续期、
配额查询、模型连通性测试与可选 Supabase 加密同步收敛到一个可脚本化的二进制里。

## 概述

codex-probe 以**本地凭证 JSON 文件**为数据模型：`--login` 走 OAuth PKCE 流程在本地
`:1455` 回调并写出凭证文件；`--renew` 原地续期单个文件或整个目录；`--status` 读取
5 小时窗口与每周窗口的剩余配额；`--apitest` 对每个模型端点发轻量请求验证可用性；
`--sync` 用 AES-256-GCM 加密本地凭证后同步到 Supabase；`--output` 把
`--status` / `--apitest` 的结果导出 CSV；`--proxy` 支持固定代理、系统代理自动探测
与强制直连。

## 已编译版本

- **1.0.3** (2026-09-18) — Go 1.26.5, CGO_ENABLED=0, static build

## 关键信息

- **源码**: https://github.com/JamesChan21/codex-probe
- **构建系统**: Go modules（入口 `./cmd/codex-probe`，非仓库根包）
- **依赖**: Go ≥ 1.22（go.mod 声明）；直接依赖 `golang.org/x/net`、`golang.org/x/sys`
- **平台**: linux/arm64 (HarmonyOS/OpenHarmony)
- **产物**: `bin/codex-probe`（静态 aarch64 ELF，stripped，约 6.1 MB）

## 鸿蒙适配要点

1. **纯 Go 静态编译**：`CGO_ENABLED=0`、`GOOS=linux`、`GOARCH=arm64`，产物无任何
   动态依赖（`llvm-readelf -d` 为空），不污染系统 `/lib`。
2. **Go linker mmap 在 HMDFS 上失败（E051/E166）** → 整个 Go 工作区（构建缓存、
   模块缓存、TMPDIR 与链接输出）放到 ext2 类可写分区
   `/data/storage/el2/base/haps/entry/files`。
3. **OHOS 上每个被 fork/exec 的 ELF 必须携带 `.codesign` section（E128/E077）**：
   未签名时执行返回 `Permission denied`（rc 126）。Go SDK 工具链（`bin/go`、
   `bin/gofmt`、`pkg/tool/linux_arm64/*`）与产物二进制都需用
   `binary-sign-tool sign -selfSign 1` 自签名。
   ⚠️ 判定是否已签名必须用 `llvm-readelf -S` 看 `.codesign` **section 头**；
   Go 二进制内嵌的 `codesign` 字样会让字符串搜索假阳性并导致漏签。
4. **上游无测试**：1.0.3 无任何 `*_test.go`，CI 仅有 GoReleaser 发布流。本适配补增
   消费者冒烟测试（6 用例 / 13 断言，鸿蒙特有测试），覆盖 `--help`、空参数、
   互斥命令、配置加载失败、`--login` 缺 `-o`、`--output` 非 `.csv` 六条路径，
   全部离线执行。

## 依赖关系

- **编译依赖**: Go 1.26.5 SDK（本地不存在时由配方自动下载 + sha256 校验 + 签名）
- **运行依赖**: 无（静态链接，仅依赖内核接口）

## 使用注意

上游对**任何真实命令**都会先做网络地域探测（`ipinfo.io` / `api.country.is` /
`ip-api.com`），检测到 `CN` 会主动退出并提示配置代理。这是上游设计行为；在鸿蒙 PC
上使用时请按上游文档配置代理或使用 `--proxy`。

## 参考资料

- **源码仓库**: https://github.com/JamesChan21/codex-probe
- **上游文档**: `docs/advanced.md`、`docs/supabase.md`（仓库内）
