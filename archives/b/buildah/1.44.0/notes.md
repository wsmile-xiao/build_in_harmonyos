# buildah 1.44.0 — 编译笔记

## 基本信息
- **软件**: buildah 1.44.0 (Go 容器镜像构建工具)
- **源码**: https://codeload.github.com/containers/buildah/tar.gz/refs/tags/v1.44.0
- **日期**: 2026-05-29（初版）/ 2026-09-17（PR #4169 接续修复）

## 编译环境
- **平台**: HarmonyOS (OpenHarmony) arm64, HongMeng Kernel 1.12.0
- **Go**: 1.25.8（自举下载，配方内置，go.mod 要求 >= 1.25.6）
- **关键问题**: Go linker mmap 在 HMDFS 上失败，需设置 GOTMPDIR/TMPDIR 到 ext2 分区

## 编译过程

### 问题1: Go linker "mapping output file failed: permission denied"（E166）
- **根因**: HMDFS 文件系统不支持 Go linker 所需的 mmap MAP_SHARED 操作
- **解决**: GOCACHE/GOTMPDIR/link 输出全部指向 `/data/storage/el2/base/haps/entry/files`（ext2，tmpfs 支持 mmap）
- **注意**: 2026-09-17 复验确认该路径在 CI worker 与本机同样可用（tlsx/argo/kubo 同款绕法）

### 问题2: entrypoint_amd64.gz 交叉编译失败
- **根因**: Makefile 默认交叉编译 amd64 entrypoint，arm64 目标必须嵌入 arm64 版本
- **解决**: 补丁 0001（Makefile）+ 0002（internal/mkcw/entrypoint.go 的 go:embed 指令）改为 entrypoint_arm64.gz

### 问题3: 二进制启动即 SIGSYS 崩溃（2026-09-17 修复，PR #4169 接续轮）
- **现象**: `buildah --version` 无输出直接被 SIGSYS 杀死
- **根因**: filepath-securejoin/pathrs-lite 的 `HasNewMountAPI`（open_tree(2), syscall 428）与
  `HasOpenat2`（openat2(2), syscall 437）可用性探测真调 syscall；**HongMeng 内核对未注册
  syscall 号返回 SIGSYS 杀进程而非 ENOSYS**，探测即死（Go 程序无法捕获同步 SIGSYS 恢复）
- **调用链**: mainInit → config.Default() → go-selinux.GetEnabled() → readConThreadSelf →
  pathrs-lite procfs.OpenProcRoot() → unix.OpenTree() → SIGSYS
- **解决**: 补丁 0003 — 在 pathrs-lite/internal/linux 新增 `hongMengKernel()`（uname 检测，
  运行时能力探测，非编译期平台宏，R8 合规）；HongMeng 内核上两个探测直接返回 false，
  走上游自带的 legacy 路径（unsafeHostProcRoot / 无 openat2 fallback）——这正是上游对
  pre-5.2 内核的标准支持路径，普通 Linux 行为完全不变
- **验证**: `buildah version 1.44.0 (image-spec 1.1.1, runtime-spec 1.3.0)` exit 0；
  `--help` exit 0

### 问题4: CGO_ENABLED=1 → 0（2026-09-17 变更）
- **初版**（2026-05-29）用 CGO_ENABLED=1 + 系统 clang 构建成功
- **本轮改为 CGO_ENABLED=0**: 实测全部 cgo 门控特性（seccomp/apparmor/btrfs/libsubid/
  systemd/sqlite）已由 build tags 排除，纯 Go 构建通过；产物为静态 ELF（42.6MB），
  与已合入 main 的 Go 配方先例（wego/tlsx/bbrew/chkbit）口径一致，规避动态链接 musl/
  sysroot 的交叉编译脆弱性
- **编译命令**（conanfile.py 内置）:
  - `go build -ldflags "-E _start -s" -o internal/mkcw/embed/entrypoint_arm64 ./internal/mkcw/embed`
  - `gzip -k9nf internal/mkcw/embed/entrypoint_arm64`
  - `go build -buildvcs=false -ldflags "-X main.GitCommit=v1.44.0 -X main.buildInfo=1747804800" -tags "containers_image_openpgp exclude_graphdriver_btrfs exclude_seccomp exclude_apparmor no_libsubid no_systemd no_sqlite nolinkednet" -o bin/buildah ./cmd/buildah`

## Build Tags 说明
- `containers_image_openpgp`: 使用 OpenPGP 签名验证（必须）
- `exclude_graphdriver_btrfs`: 排除 btrfs 图驱动（不可用）
- `exclude_seccomp`: 排除 seccomp 支持（libseccomp 不可用）
- `exclude_apparmor`: 排除 apparmor 支持（libapparmor 不可用）
- `no_libsubid`: 不使用 libsubid
- `no_systemd`: 不使用 systemd
- `no_sqlite`: 不使用 sqlite 存储
- `nolinkednet`: 使用动态网络配置

## 安装产物
- bin/buildah (42.6MB, AArch64 静态 ELF, OHOS 签名)
- share/bash-completion/completions/buildah

## 已知平台限制（待专家分析）
**rootless 容器存储不可用**: containers/storage 的 rootless 模式需要 user namespace
（fork + CLONE_NEWUSER re-exec /proc/self/exe），HongMeng 内核策略禁止普通应用创建
userns（fork 返回 EAGAIN），故 `buildah images/from/build` 等需要存储初始化的命令无法
在非特权用户下完成。这是内核能力边界（与 seccomp/apparmor 同类），非配方层可修复：
- 已验证: fork/exec /proc/self/exe 本身正常；仅 CLONE_NEWUSER clone 被拒
- 可能方向: 内核开放受限 userns / 以 root 特权服务形态集成 / 等 OHOS 容器子系统演进
- 详见 PR #4169 描述与本次提交说明

## 上游测试用例（R51 三步法）
- 上游 `*_test.go` 清点: buildah 仓库自带 go test 套件（add_test.go/buildah_test.go 等
  数十个文件），依赖完整容器运行环境（需要 root/userns/mount/网络），在 HarmonyOS
  无 userns 环境下不可运行（真实技术原因）
- test_package 覆盖: ELF AArch64 结构校验 + `buildah --version` 真实执行断言
  （SIGSYS 修复后必须 exit 0，不再作为"已知限制"容忍）

**编译结束**: 2026-09-17
**最终状态**: built
---

**编译结束**: 2026-09-17 17:55
**最终状态**: built
