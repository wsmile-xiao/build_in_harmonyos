# aliyunpan 0.4.0 HarmonyOS PC notes

## 适配概要

- 上游项目: github.com/tickstep/aliyunpan (tag v0.4.0, 2026-06-29 发布)
- 平台任务: 库名 aliyunpan, 版本 0.4.0, Issue #2030, 分支 feat/aliyunpan-0.4.0
- 语言: Go (go.mod: go 1.22)，非任务页声称的 C++ —— 以实际源码为准
- 许可证: Apache-2.0
- 构建系统: Go module，单命令 `aliyunpan`，主入口在仓库根 (main.go)
- OHOS 策略: CGO_ENABLED=0 纯 Go 构建 linux/arm64 可执行文件

## 身份映射

- 平台身份: aliyunpan / 0.4.0 / Issue #2030
- 上游身份: tickstep/aliyunpan / v0.4.0 / Apache-2.0
- 归档身份: conan aliyunpan/0.4.0 @ archives/a/aliyunpan/0.4.0/
- 三者名称一致，无需额外映射说明。

## 构建与验证

- 源码: GitHub tag v0.4.0 tarball，SHA256 b68726a13bcaba6353b1c89950695a71397ad2c722aa25750b82583701121fdd
  （gh-proxy.com 与 ghfast.top 两个镜像下载结果一致；github.com 直连在本环境不可达）
- Go 工具链: go1.26.3 (mirrors.aliyun.com，SHA256 与 murex 归档 conandata 一致，本机实测一致)
- 构建命令: `go build -trimpath -ldflags "-s -w -X main.Version=v0.4.0" -o aliyunpan .`
- 链接输出、GOCACHE/GOMODCACHE/TMPDIR 全部置于 /data/storage/el2/base/cache 非 hmdfs 工作区（E051）
- Go 工具链与产物 ELF 用 binary-sign-tool 签名（E077）

## 上游测试

- 上游 19 个 *_test.go 文件、61 个 `func Test...` 用例。
- 本机 OHOS 环境实测：60 个用例通过，0 失败。
- TestBoltUltraFiles (internal/syncdrive/bolt_db_test.go) 硬编码作者 macOS 路径
  (/Volumes/DataDisk3T/test/local.bolt 与 /Volumes/Downloads)，在无这些路径的任何机器上
  os.Lstat 失败后把 nil FileInfo 放入切片，walkFunc 中 info.Name() 触发 nil 解引用 panic。
  该用例在任何非作者机器上均不可运行，属上游缺陷；配方 build() 用 `go test -skip TestBoltUltraFiles`
  排除（CI 门禁需要测试命令整体通过），统计中记为 errors=1，不作为 passed 或 skip 计入。
  测试语义（断言/数据/用例选择）未做任何修改。
- `go test ./...` 原始完整运行输出见 reports/。

## 消费者测试 (test_package)

- test_aliyunpan.sh 实际执行打包后的 `aliyunpan --version`（断言 v0.4.0）与 `aliyunpan help`（断言应用名与 VERSION 段）。
- 3 个断言全部通过。

## 与先例的差异

- 参考仓库内 aicommit 0.6.5 / murex 7.2.1001 的 Go CLI 配方模式；
- aliyunpan 需要执行上游测试，且存在一个上游不可运行用例，采用 -skip 排除并如实记录。
---

**编译结束**: 2026-08-11 07:50
**最终状态**: built
