- **三方库名称**：metalog
- **上游版本**：20260221
- **上游仓库地址**：https://github.com/hvisage/metalog
- **适配路径**：路径 A（基础适配）
- **使用知识库**：复用正式条目 E007（Autotools triplet）、E011（HMDFS 临时目录权限）与 E528（Conan 环境下 configure shell 覆盖）；本 PR 未新增知识库草稿

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 0 | 上游 tag 无测试目录、测试源文件或测试目标 |
| 集成测试 | 0 | 上游无自动化测试套件 |
| 其他测试 | 0 | 上游无独立测试用例 |
| **合计** | **0** | 基于 tag `20260221` 源码目录与 Automake 目标核验 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------:|------------|------|
| 单元测试 | 0 | 不变 | 未伪称上游包含单元测试 |
| 集成测试 | 4 | 新增 4 | CLI 版本/帮助、有效配置、无效配置；测试模式不启动 daemon、不绑定系统日志 socket |
| 鸿蒙特有测试 | 1 | 新增 1 | 校验打包 ELF 为 64 位 AArch64（e_machine=183） |
| **合计** | **5** | **新增 5** | 消费者测试断言在 `test_package/MANIFEST.yml` 逐项登记 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，上游没有测试用例，本移植未修改上游测试文件。
- [ ] **是**，存在对上游测试用例的修改。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游 tag 没有测试套件，本适配补充了 5 项检查。

补全范围：CLI `--version` 与 `--help`、有效/无效配置解析，以及 HarmonyOS AArch64 ELF ABI。测试通过 `--test-config` 校验配置，不占用 `/dev/log`，不要求 root。

新增测试文件：

1. `test_package/test_metalog.py` — 4 项 CLI/配置集成检查及 1 项 HarmonyOS ELF ABI 检查。

## 验证结果

- 编译状态：最新 head `0e2c988c` 已将 OHOS configure 工作目录设为 `build_folder`，并将 make 固定为 `-j1`；该 head 的 CI 结果待确认。父 head `d2c75040` 的 CI #67293 已通过 L0、KC、autoreconf 与 configure，但 `make -j20` 因 HMDFS 拒绝 GNU make jobserver FIFO（`mkfifo ... Operation not permitted`）失败，同时暴露 configure 与 make 工作目录不一致。更早的 #66790 是 worker-prep/git-clone SSH bridge connection refused。此前真机 5/5 测试来自旧 head，不代表当前 head。
- 上游测试用例通过率：0/0（无上游测试，未将其记为通过）
- 新增测试用例通过率：最新 head 尚未实跑；CI #67293 在进入 test_package 前编译失败。此前版本 HarmonyOS AArch64 真机 5/5（ABI 检查与 4 项运行时检查均通过），该结果不记为当前 head 通过。

## 补充说明

- 构建依赖 PCRE2；zlib 为可选依赖，`with_compress=False` 时使用上游 `--without-compress`。
- 构建时使用 `automake/1.18`、`autoconf-archive/2024.10.16` 和 `pkgconf/3.0.5` 提供 autoreconf、`AX_CHECK_COMPILE_FLAG` 与 `PKG_CHECK_MODULES` 所需构建工具/宏；这些项目不进入运行依赖。
- 上述旧版测试数据来自此前本地 HarmonyOS AArch64 真机 Conan test_package 日志；CI #66654 定位到缺少构建工具/宏，CI #66662/#66668/#66682 定位到 profile 注入的失效 shell 路径，#66783 复现旧 config.sub 补丁语法错误，#66790 在 worker-prep/git-clone 阶段因 SSH bridge connection refused 失败，#67293 则暴露了 configure 工作目录及 GNU make jobserver FIFO 两个内容问题。最新 head 修正后尚未实测，旧 head 的 5/5 不计入当前结果。
