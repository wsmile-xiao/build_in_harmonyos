# zrepl 0.7.0 — 适配笔记（路径 A）

## 三重身份映射

| 身份 | 值 |
|------|-----|
| 平台 | zrepl / 0.7.0 / Issue（任务页）/ feat/zrepl-0.7.0 |
| 上游 | zrepl/zrepl（github.com/zrepl/zrepl），tag v0.7.0，MIT |
| 归档 | Conan zrepl/0.7.0，archives/z/zrepl/0.7.0/ |

三者名称与版本完全一致，无需映射解释。上游为纯 Go 项目（CLI + daemon，无 C/C++ 目标库），属于应用类（package_type=application）路径 A 适配。

## 上游核验

- 源码：https://github.com/zrepl/zrepl/archive/refs/tags/v0.7.0.tar.gz（与 codeload .../tar.gz/refs/tags/v0.7.0 形态字节一致；conan get() 按扩展名选解压器，必须用 .tar.gz 结尾的 URL）
- SHA256（本机 + OHOS 设备双端实测一致，434419 字节）：d451ad1d05a0afdc752daf1dada9327aa338f691eca91e1c8fc9828eebd89757
- 许可证：MIT（LICENSE，Copyright (c) 2017-2018 Christian Schwarz）
- 语言：Go（go.mod: go 1.24.13 / toolchain go1.25.7，module github.com/zrepl/zrepl；0.7.0 起入口为仓库根 main.go，无 cmd/ 目录）
- 构建系统：Go + Makefile（.DEFAULT_GOAL=zrepl-bin；GO_ENV_VARS=CGO_ENABLED=0；GO_MOD_READONLY=-mod=readonly；GO_LDFLAGS 注入 internal/version.zreplVersion）
- 依赖：~31 个纯 Go 直接依赖（grpc/prometheus/tcell/cobra/testify 等），无 vendor/ → 需 GOPROXY 镜像拉取模块图（设备实测 goproxy.cn 与 mirrors.aliyun.com 均可达；sumdb 校验经 GOPROXY 代理，默认开启）
- 版本变量：internal/version/version.go `var zreplVersion string`（包级变量，-ldflags -X 注入有效；与 ld-find-code-refs 的 const 情形相反）
- CLI 结构：cobra 根命令 `zrepl`；子命令 version/configcheck/daemon/status/signal/stdinserver/pprof/test/migrate/zfs-abstractions/gencompletion
  - `zrepl version --show=client`：NoRequireConfig，打印 "client: zrepl version=... go=... GOOS=... GOARCH=... Compiler=..."，无 daemon/配置即可退出 0
  - 注意：`zrepl version`（不带 --show=client）会继续连 daemon control socket，无配置时 exit 1 —— 冒烟必须用 --show=client
  - `zrepl configcheck --config <file>`：解析配置并校验；空配置合法（上游自身测试 TestSampleConfigsAreParsedWithoutErrors 解析 samples/empty.yml）
- 测试入口：make test-go = `CGO_ENABLED=0 go test ./...`；61 个 _test.go / 38 个包 / 131 个顶层 func Test（其中 1 个是 internal/platformtest/harness 里名为 TestMain 的普通用例，非 testing.M 装配器）
  - 单元测试全部纯 Go：destroy 批量测试用 mockBatchDestroy（不触 zfs 二进制）；zfscmd 测试仅执行仓库自带 shell fixture（/bin/sh 与 #!/usr/bin/env bash，设备均具备）；无 git 二进制执行、无 API key 依赖
  - platformtest（make platformtest）：需要真 ZFS 内核模块（/dev/zfs）——HarmonyOS HongMeng kernel 1.12.0 无 zfs kmod、无 zfs/zpool 用户态 → 本平台不适用，未运行（NOT_RUN，平台阻塞，非适配缺陷）

## 实现要点

- conanfile.py：Go 应用配方（基于 archives/l/ld-find-code-refs 先例，该先例的辅助函数即 Go 应用配方范式；与 unpackerr/go 工具链先例同源）：
  - `go mod download`（GOPROXY=https://goproxy.cn,direct，可用 OHOS_GO_PROXY 覆盖）→ `go test -mod=readonly ./...`（OHOS 上 `-exec` 自签 wrapper）→ `go build -mod=readonly -trimpath -ldflags "-s -w -X .../zreplVersion=0.7.0" -buildvcs=false -o zrepl .`
  - 与先例的关键差异：无 vendor/（先例 GOPROXY=off 不可用）→ 走镜像拉模块；sumdb 校验保持开启（经 GOPROXY 代理），供应链校验不降级
  - Go 工具链 go1.26.3（linux-amd64/linux-arm64）自 mirrors.aliyun.com 下载，SHA256 已在设备实测复核，置于模块树外；GOTOOLCHAIN=local，本地 1.26.3 >= go.mod 要求的 1.24.13，无需降级 go.mod（规避 gobuster 反例的降版本做法）
  - GOCACHE/GOMODCACHE/GOPATH/TMPDIR/GOTMPDIR/链接输出置于非 hmfs 工作区 /data/storage/el2/base/cache（规避 Go linker mmap 限制 E051/E134/E166 —— gobuster 反例把输出放 hmfs/tmp 导致链接失败）
  - 产物与工具链 ELF 经 binary-sign-tool 自签（E077）；go test 环境 PATH 前置 /data/service/hnp/bin（env bash 探测需要）与工具链 bin
- test_package：真实消费打包产物：
  1. `zrepl version --show=client` 断言输出含 zrepl version=0.7.0 与 GOARCH=arm64（-X 注入变量）
  2. `zrepl --help` 退出码 0 且列出 version/configcheck 子命令
  3. `zrepl configcheck --config <空文件>` 正向解析退出 0
  4. 破坏性反向验证：未知子命令必须被 cobra 拒绝（exit != 0）
- commands.json：CLI 工具（R38），软件级声明 binary=true
- 上游补丁（1 个，最小可解释，仅触及测试 fixture，不触及产品代码）：
  - `internal/daemon/hooks/test/test-large-stdout.sh`：原 fixture 用无限 `while printf` 管道进 `head -c 2MiB`，其终止依赖"写端进程自身"死于 SIGPIPE——主流 /bin/sh（bash/dash/mksh）的 printf 为内建，循环进程即写端，head 退出后内建写端死于 SIGPIPE、循环终结。OHOS /bin/sh（toybox）无 printf 内建（`sh -c 'type printf'` → "printf is an alias for printf"，外部 applet），每轮循环 fork 新外部写端，单个写端的 SIGPIPE 死亡不终结 `while :` 循环 → 管线永无 EOF → hook cmd.Wait 挂死 → TestHooks/exceed_buffer_limit 10 分钟 go-test 超时 panic（CI run2 实测 FAIL 600.612s）。Curator/Auditor 有界控制探针（P1-P4，全部 timeout -s KILL 包裹）证实：同设备简单管线的 EPIPE/SIGPIPE 投递正常（bash 内建写端循环、登录 shell 建管外部 seq、toybox sh 建管 seq 均读端退出后同秒终结；裸 echo 循环因 toybox sh 进程内执行也同秒终结，而 /bin/echo、/bin/printf 外部循环同样挂死）——决定变量是写端在循环进程内（内建）还是 fork 外部 applet，而非内核级 EPIPE 缺失；两种挂死形态（fork 再生 spin / 写端阻塞 write 呈 TERM 免疫）的确切切换条件尚未定性，按 open point 记录。修复改为 `dd if=/dev/zero bs=$((2<<20)) count=1` 有限生产者；Go 侧用 circlog（1MiB 环形缓冲）持续 drain 到 EOF，断言仅校验截断后长度 == 1<<20，与内容无关，测试语义在 POSIX 与 OHOS 上均保持。
- 零产品代码 patch：源码产品部分无需任何修改即可在 OHOS 上构建与通过测试。

## 平台能力边界（如实记录）

- OHOS/HongMeng kernel 1.12.0 无 /dev/zfs、无 zfs kmod，也无 zfs/zpool 用户态命令：zrepl 的复制/快照核心功能在本设备上无法运行。这是平台运行时环境限制，非本适配缺陷。
- 交付目标 = 构建成功 + 上游 go test 通过 + test_package CLI 冒烟（version / --help / configcheck / 未知子命令反向）。
- make platformtest 需要真 ZFS → NOT_RUN（不适用），如上"上游核验"节所记。
- zfs 用户态库（zfs-linux）为另一并行 run，且即便其合入也无内核 kmod，故本配方不将其建模为 conan 依赖，仅作为可选运行时环境。

## 验证结果

（由实际命令日志回填，权威 CI 日志存设备 tmp run 目录 builder/ci-run-3.log）

- 权威 CI run3：G0/KC/JC/L0/L1/L1e/L2/L4/L5 全部 pass，"All packages built and tested successfully"，1/1 包成功（前两轮：run1 L0k commands.json 位置修正；run2 hooks 包 10 分钟超时 → fixture 写端 fork 再生机理（/bin/sh 无 printf 内建）→ fixture patch 修复）。go test 全量：38 个 ok 包（其中 internal/rpc/dataconn 为纯测试辅助代码，ok[no tests to run]），131 顶层 func Test 全过
- 上游测试：go test -mod=readonly ./... 在 OHOS arm64 真实运行：37 个含测试包全部 ok，131 个顶层 func Test 全部通过（0 失败/0 跳过/0 panic；internal/rpc/dataconn 为测试辅助代码无 Test 函数，ok[no tests to run]）；hooks 包修复后 ok 3.018s。run1 阶段模块图经 GOPROXY=goproxy.cn 拉取 + sumdb 校验通过，Go 工具链 go1.26.3 自 mirrors.aliyun.com 下载 SHA256 复核一致
- 消费者测试（test_package）：4 断言全过——`zrepl version --show=client` 输出 "client: zrepl version=0.7.0 go=go1.26.3 GOOS=linux GOARCH=arm64 Compiler=gc"（-X 注入生效）、`--help` 列出子命令、`configcheck` 空配置解析通过、未知子命令被 cobra 拒绝（exit != 0）；CI L1e 破坏性反向验证（挪走 bin/）确认测试真实依赖产物
- platformtest（make platformtest）：NOT_RUN——需真 ZFS 内核模块（/dev/zfs），HongMeng 1.12.0 无 zfs kmod，平台不适用（非适配缺陷，见"平台能力边界"）

## 未做事项

- 未 push（hook 强制拒绝）；未创建/修改 PR；未任务平台提审
- 未修改 ci/**、其他库目录、knowledge/ 正式条目
