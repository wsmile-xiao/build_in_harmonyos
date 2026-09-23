# cascadia 1.5.1 适配笔记

## 基本信息

- 上游仓库：https://github.com/suntong/cascadia
- 上游版本：v1.5.1（2026-05-28，修复安全漏洞与 GoReleaser 配置）
- 许可证：MIT
- 构建系统：Go（custom，`go build .`，main 在仓库根）
- Go 要求：go.mod 声明 go 1.25.0，配方要求 Go >= 1.25（SDK bootstrap 复用 1.25.12）
- 状态：built（待真机预检回填实测数字）
- 适配路径：路径 A（基础适配）

## 上游测试审计（源码级清点，待真机实测回填通过率）

| 测试函数 | 文件 | 说明 |
|----------|------|------|
| TestSelectors | cascadia_test.go | 表驱动选择器矩阵，约 70 组 HTML/selector/期望结果，纯内存测试，不依赖二进制 |
| TestPiece | piece_test.go | 经 prop_test.go 的 testCases/testIt 驱动 `../cascadia` 二进制 + `diff` 对比 test/*.ref；含 Piece raw html 1 例 + Piece Attributes 5 例 |
| TestPieceGoqr | piece_test.go | GOQR 属性抽取 2 例（piece_goqr、piece_goqr_missing），同样依赖二进制 + diff |
| 辅助 | prop_test.go | testIt/testCases 辅助函数，无独立 Test |

- 上游测试入口：`go test -v -count=1 ./...`，共 3 个顶层 Test。
- 依赖：`test/` 目录下 opt_piece_attr.html、opt_piece_script.html 等夹具 + .ref 期望文件；运行环境需要 `diff` 命令。
- 配方处理：build() 先构建二进制并暂存为 `<source_folder>/cascadia`（满足 `../cascadia` 引用），再跑全量 `go test ./...`，计数取自 `--- PASS/FAIL/SKIP` 行并输出 `HMBS_UPSTREAM_TEST_RESULT` 标记；OHOS 下经 `-exec` 签名包装器执行 *.test 产物。

## 编译步骤

1. 下载源码：https://github.com/suntong/cascadia/archive/refs/tags/v1.5.1.tar.gz
   sha256=228ee980bc823adf21874dc4cd76c7832fca39b48fed4b9e014927889dd7051a
2. `go mod download`（GOPROXY=https://goproxy.cn,https://proxy.golang.org,direct）
3. `go build -trimpath -ldflags "-s -w" -o <bin>/cascadia .`（OHOS 时先在 go-workspace link-out 链接再拷贝，规避 HMDFS mmap 失败）
4. binary-sign-tool 自签名（仅 OHOS）
5. `go test -v -count=1 ./...`（OHOS 时带 `-exec` 签名包装器）
6. test_package：test.sh 对安装后的二进制做 3 组真实功能断言（help 输出、单元素 CSS 抽取、ATTR piece 抽取），输出 `HMBS_TEST_PACKAGE_RESULT` 标记

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 cascadia_main.go 硬编码 version="1.5.0" | v1.5.1 tag 未同步版本常量 | 不注入 -X（无注入点），test_package 不断言版本号，只断言真实抽取功能 |
| 2 | piece/GOQR 测试需要仓库根二进制 | prop_test.go 写死 cmdTest="../cascadia" | build() 内把刚构建的二进制拷贝到 source_folder/cascadia 再跑测试，跑完删除 |
| 3 | OHOS 上 go test 产物 permission denied | *.test ELF 无 .codesign 段被拦截 | 复用 addchain 的 -exec 签名包装器模式 |
| 4 | Go linker 在 HMDFS 上失败 | 真机包目录文件系统不支持 mmap 链接输出 | 复用 caddy/addchain 的 link-out 工作区模式 |

## 源码修改

无补丁，纯 Go 编译无需源码修改。

## 依赖版本

- Go >= 1.25（bootstrap SDK 1.25.12，arm64/amd64 双归档）
- clang 15（仅环境占位，本包 CGO_ENABLED=0）
- Go 模块依赖：goquery v1.10.3、andybalholm/cascadia v1.3.3、mkideal/cli v0.2.7、x/net v0.54.0（全部经 go mod 自动下载）

## 验证结果

- 本地（Windows 执行器）：仅完成配方编写与源码审计，未运行 conan（按任务守则，编译验证统一在真机预检执行）。
- 真机预检：待 HMBS 后台执行后回填 `go test` 实测计数与 test_package 3/3 结果。
- 防证伪备忘：上游 TestSelectors 为内存断言（非空比对）；piece 类测试依赖 .ref 非空 + diff 真比对，若预检出现全 PASS，需确认 test/*.ref 非空且 `diff` 真实存在。

## 交付物

| 文件 | 说明 |
|------|------|
| bin/cascadia | Go 编译的 CLI 二进制（OHOS 上为已签名 ELF） |
| licenses/LICENSE | 上游 MIT 许可证 |

## 注意事项

- 本包为纯 CLI 工具（package_type=application），commands.json 在软件级目录声明 type=tool。
- conandata.yml 仅写官方原始 URL，CI 自动追加镜像 fallback。
- test_package 的 3 个断言均为真实调用二进制的端到端抽取，非空壳测试。
