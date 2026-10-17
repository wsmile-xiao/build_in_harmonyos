# buildah 1.44.0 — 测试报告

## 编译测试
- **日期**: 2026-09-17（PR #4169 接续修复轮）
- **结果**: PASS

### 编译成功（conan create 本地 W3 复验）
- Go 工具链自举: 官方 SDK go1.25.8 linux-arm64（golang.google.cn/dl.google.com, SHA256 校验, OHOS ELF 重签）
- CGO_ENABLED=0 纯静态构建 (AArch64 ELF, 42.6MB)
- Build tags: containers_image_openpgp, exclude_graphdriver_btrfs, exclude_seccomp, exclude_apparmor, no_libsubid, no_systemd, no_sqlite, nolinkednet
- mkcw embed: entrypoint_arm64.gz（补丁 0001/0002）

### 功能测试（test_package, conan create 内置执行）
- [test] buildah found at: <pkg>/bin/buildah ✓
- [test] ELF AArch64: OK ✓（结构校验: EM_AARCH64=183）
- buildah version 1.44.0 (image-spec 1.1.1, runtime-spec 1.3.0) ✓ **二进制真实执行成功**
- [test] buildah --version succeeded ✓ exit 0

### SIGSYS 修复验证（2026-09-17 新增）
- 修复前: `buildah --version` 被 SIGSYS 杀死（open_tree(2) 探测, HongMeng 内核对未实现 syscall 返回 SIGSYS 而非 ENOSYS）
- 修复后（补丁 0003 runtime uname 检测 + legacy 路径）: `--version` / `--help` exit 0 正常输出
- 运行环境: HarmonyOS PC, HongMeng Kernel 1.12.0, arm64

### 上游测试用例（R51 三步法）
- 清点: 上游自带 go test 套件（*_test.go 数十个文件, add_test.go/buildah_test.go/commit_test.go 等）
- 不可运行的真实技术原因: 单元/集成测试依赖完整容器运行时（root 权限/user namespace/mount/网络命名空间/runc）;
  HongMeng 内核禁止普通应用创建 user namespace（fork+CLONE_NEWUSER → EAGAIN），无特权测试无法执行
- test_package 覆盖: ELF 结构断言 + 二进制真实执行（--version 输出版本号, exit 0 硬断言, SIGSYS 视为缺陷）

### 已知平台限制（待专家分析, 非测试失败）
- rootless 容器存储（images/from/build 等子命令）需 user namespace, 内核策略禁止, 详见 notes.md

**结论**: PASS
