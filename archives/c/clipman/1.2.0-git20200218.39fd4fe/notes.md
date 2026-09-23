# clipman 1.2.0-git20200218.39fd4fe 适配笔记

## 编译环境
- 构建系统: Go (custom)
- 编译日期: 2026-09-09（首轮工作树，真机预检待 HMBS 后台执行）
- 编译器: clang/clang++ + Go（caddy 同款探测：环境变量 → ~/usr/local/go1263 → PATH → bootstrap）
- 状态: built

## 上游确认

| 项目 | 结论 |
|------|------|
| 上游仓库 | https://github.com/chmouel/clipman（yory8 原仓库已删除，chmouel 为继承其完整历史的维护中 fork，90 stars，含全部 tags） |
| 版本含义 | Debian 快照版本号 `1.2.0+git20200218.39fd4fe` 对应上游 commit `39fd4fe0e7cbb3abb41cb6e5ebb961f6b75fd4e1`（2020-02-18，docs: small formatting fix，author yory8） |
| 源码归档 | `https://github.com/chmouel/clipman/archive/39fd4fe0e7cbb3abb41cb6e5ebb961f6b75fd4e1.tar.gz`，19028 字节，sha256 `9947a1e3e6ac181a24fb495fc4c624725f5ef35c9275f3338948c72755f5ca2f`（已本地下载验算） |
| 语言/模块 | 纯 Go，`module github.com/yory8/clipman`，go 1.13 directive；唯一直接依赖 `gopkg.in/alecthomas/kingpin.v2 v2.2.6` |
| 上游测试 | 无（归档树仅 3 个 .go 文件，无 `*_test.go`、无 tests/ 目录、无 Makefile；README 亦无测试说明）→ 走 `no_tests` 审计路径 |

## 编译步骤

1. 下载源码（conan `get()`，strip_root=True，顶层目录 `clipman-39fd4fe…/`）。
2. `generate()` 写入 `clipman_go_env`：CGO_ENABLED=1、GOOS=linux（OHOS 映射）、GOARCH=arm64、GOPROXY（goproxy.cn 优先）、GOTOOLCHAIN=local、GOFLAGS=-mod=mod、私有 GOCACHE/GOMODCACHE/TMPDIR、Go bin 前置 PATH。
3. `build()`：`go mod download` 后 `go build -trimpath -o <out> .`（仓库根即 main 包；上游版本号为 main.go 常量 `1.2.0`，无需 ldflags 注入；不用 `-s` 以保留 Go build info）。
4. OHOS 下经 binary-sign-tool 自签名后装入 `bin/clipman`；`COPYING` → `licenses/`，`docs/clipman.1` → `share/man/man1/`。
5. 无补丁：纯 Go 编译，无需源码修改。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | yory8/clipman 上游仓库已删除，源码 URL 定点困难 | 原作者仓库不存在，`git ls-remote` 报 Repository not found | 改用继承完整历史的维护中 fork chmouel/clipman，经 GitHub API 确认 commit 39fd4fe（日期/作者/信息与 Debian 快照完全吻合），归档 URL 指向该 fork 的 commit 归档 |
| 2 | 上游无测试套件，无法执行上游测试 | 快照仅 3 个 .go 文件，无测试框架痕迹 | 复用 bankstown-lv2 的 no_tests 模式：test_package/test_audit.py 每轮真机重新下载同 URL+sha256 归档并扫描，输出 `HMBS_UPSTREAM_TEST_RESULT`（status=no_tests）；MANIFEST.yml 写入 `upstream_tests_exist: false` + 逐文件审计 |
| 3 | clear/restore 子命令依赖外部程序 | `clear --all` 先执行 `wl-copy -c`（缺失则 log.Fatal），restore/pick 非 STDOUT 路径需要 wofi/dmenu 等选择器 | test_clipman.sh 只覆盖无外部依赖路径：`--version`、`store -P`（跳过 wl-copy 持久化）、`pick --tool STDOUT`、`--help`；notes 与 PR 正文如实声明未覆盖范围 |

## 源码修改

无补丁，纯 Go 编译无需源码修改。

## 依赖版本

- Go >= 1.25（go.mod 仅声明 go 1.13 语言版本，现代工具链可构建；GOTOOLCHAIN=local 禁止自动升级）
- 运行时 Go 模块依赖：kingpin.v2 v2.2.6（经 GOPROXY 自动拉取）
- clang 15（CGO_ENABLED=1 需要 C 工具链存在；无实际 CGO 代码）
- 适配期参考：caddy/2.11.2-r1（Go 配方模式）、bankstown-lv2/1.1.0（no_tests 审计模式）

## 验证结果

首轮仅完成未提交工作树，真机 `conan create` 预检由 HMBS 后台执行，待回填：

```bash
conan create . --user=ohpcd --channel=stable -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# 预期：Testing package 阶段依次运行 test_clipman.sh（6 断言）与 test_audit.py（no_tests 审计），
# 日志含 HMBS_TEST_PACKAGE_RESULT 与 HMBS_UPSTREAM_TEST_RESULT 两行标记
```

本地已完成的校验：
- 上游归档下载 + sha256 验算一致（9947a1e3…5ca2f）
- 归档内容列举：12 项，与 GitHub API 树一致，strip_root 可用
- `python -m py_compile` 通过：主 conanfile.py、test_package/conanfile.py、test_audit.py
- YAML/JSON 解析通过：conandata.yml、两级 manifest.yaml、test_package/MANIFEST.yml、commands.json

## 交付物

| 文件 | 说明 |
|------|------|
| bin/clipman | Go 编译的 arm64 ELF 二进制（OHOS 下经 binary-sign-tool 自签名） |
| share/man/man1/clipman.1 | 上游 man 手册 |
| licenses/COPYING | GPL-3.0 许可证文本 |

## 注意事项

- `test_clipman.sh` 的临时 histpath 必须走 HMBS_TMPDIR/TMPDIR，绝不写入 test_package 源码目录（conan test_package 的 build_folder 即源码目录，bankstown 先例）。
- `test_audit.py` 优先使用 test_package/conanfile.py 经 `conan.tools.files.download` 拉取的 tarball（CI worker 的系统 python 缺 ssl 模块，裸 urllib 无法处理 https）。
- `store` 测试固定使用 `-P`；`pick` 固定 `--tool STDOUT`。任何引入 wl-copy/选择器的用例在真机失败时应直接删除而非加条件跳过（跳过会被 HMBS 判为 incomplete）。
- 反证要求：若 HMBS 对 6 断言的真实性提出质疑，可把二进制换成 `exit 1` 桩重跑，harness 应报 `passedCount=0`（grep -c 计数机制保证）。
