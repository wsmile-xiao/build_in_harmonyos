# unpackerr 0.15.2 — 适配笔记（路径 A）

## 三重身份映射

| 身份 | 值 |
|------|-----|
| 平台 | unpackerr / 0.15.2 / Issue #2083 / feat/unpackerr-0.15.2 |
| 上游 | Unpackerr/unpackerr（github.com/Unpackerr/unpackerr），tag v0.15.2，MIT |
| 归档 | Conan unpackerr/0.15.2，archives/u/unpackerr/0.15.2/ |

三者名称与版本完全一致，无需映射解释。任务页 C++ 标签不准确：该软件为纯 Go 守护进程，无 C/C++ 目标库，属于应用类（package_type=application）路径 A 适配。

## 上游核验

- 源码：https://github.com/Unpackerr/unpackerr/archive/refs/tags/v0.15.2.tar.gz
- SHA256（实测下载）：a3279d1d66964f392940097dd904b6e66c5a0ef4f1370fc2ca87d0ac58a72573
- 许可证：MIT（LICENSE 文件头版权 2018-2022 David Newhall II / 2023-2026 Go Lift）
- 语言：Go（go.mod: go 1.26.0，module github.com/Unpackerr/unpackerr）
- 构建系统：Go + Makefile（`go build` 根包 main.go，产物 `unpackerr`）
- 依赖：无 vendor/，模块依赖经 GOPROXY 拉取（golift.io/starr、golift.io/xtractr、prometheus 等）
- 测试入口：`go test ./...`，3 个测试文件 15 个测试函数：
  - pkg/unpackerr/folder_recursion_test.go（4）
  - pkg/unpackerr/folder_test.go（5）
  - pkg/unpackerr/start_test.go（6）

## 实现要点

- conanfile.py：Go 应用配方（参考 algernon/murex 先例）：
  - `go mod download` → `go test ./...`（OHOS 上 `-exec` 自签 wrapper）→ `go build -trimpath -ldflags "-s -w -X golift.io/version.Version=0.15.2" -buildvcs=false -o unpackerr .`
  - Go 工具链 go1.26.3（linux-amd64/linux-arm64）自 mirrors.aliyun.com 下载，SHA256 已实测校验，置于模块树外
  - GOCACHE/GOMODCACHE/GOPATH/TMPDIR/链接输出置于非 hmfs 工作区（/data/storage/el2/...），规避 E051/E134/E166
  - 产物与工具链 ELF 经 binary-sign-tool 自签（E077）
- test_package：真实消费打包产物：
  1. `unpackerr --version` 断言输出含 unpackerr 与 0.15.2（ldflags 注入 golift.io/version.Version）
  2. `unpackerr --help` 退出码 0
  3. 最小 TOML 配置启动守护进程，断言启动日志含 "Starting!"，随后 kill 清理
- commands.json：unpackerr 是 CLI 工具（R38），软件级声明 binary=true

## 验证结果

（由实际命令日志填写，见 reports/ 与最终报告）

- conan-verify：G0-G4 + L2/L4/L5 结果
- finish：外层退出码与状态
- 上游测试：15 用例通过情况
- 消费者测试：3 场景 4 断言

## 未做事项

- 未创建/修改 PR；未 /ai review；未 /rebuild；未任务平台提审（本轮授权范围 commit_and_push）
---

**编译结束**: 2026-08-12 17:50
**最终状态**: built
