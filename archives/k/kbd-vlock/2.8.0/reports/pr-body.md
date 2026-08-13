- **三方库名称**：kbd-vlock
- **上游版本**：2.8.0
- **上游仓库地址**：https://www.kernel.org/pub/linux/utils/kbd/kbd-2.8.0.tar.xz
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无新增知识草稿；参考本仓库既有 HarmonyOS 适配共性问题记录

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | kbd 2.8.0 上游 `tests/` 覆盖 libcommon、libkeymap、keymap 数据和其他 kbd 工具，未发现独立 vlock 测试用例 |
| 集成测试 | 0 | 未发现独立 vlock 集成测试 |
| 其他测试 | 0 | 完整 kbd `make check` 不计入本组件包的 vlock 上游测试通过率 |
| **合计** | **0** | vlock 组件无独立上游测试用例 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 无独立上游 vlock 单元测试，未新增单元测试 |
| 集成测试 | 0 | 不变 | vlock 是交互式 PAM/TTY 锁屏工具，未新增交互式集成测试 |
| 鸿蒙特有测试 | 3 | 新增 | `test_package/test_smoke.py` 在 Conan runenv 下执行 `vlock --version` 和 `vlock --help`，断言版本号、Usage 文本和 vlock 标识 |
| **合计** | **3** | **+3** | 新增 3 条 smoke 断言 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无 vlock 组件独立测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：为 vlock 命令行可运行性新增 3 条 smoke 断言。
> - **补全原因**：上游 kbd 2.8.0 的测试套件未提供独立 vlock 测试；vlock 本体是交互式 PAM/TTY 锁屏工具，不适合在自动化 CI 中执行真实锁屏流程。
> - **新增测试文件清单**：
>   1. `archives/k/kbd-vlock/2.8.0/test_package/test_smoke.py` — 执行 `vlock --version` 和 `vlock --help`，验证版本号、Usage 文本和 vlock 标识。
>   2. `archives/k/kbd-vlock/2.8.0/test_package/conanfile.py` — 通过 Conan `VirtualRunEnv` 提供 PAM 运行时库路径并执行 smoke 脚本。
>   3. `archives/k/kbd-vlock/2.8.0/test_package/MANIFEST.yml` — 声明上游测试口径与新增 smoke 测试。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（vlock 组件无独立上游测试用例，不适用；未将 kbd 全量 `tests/` 中其他工具用例计入）
- 新增测试用例通过率：3/3（100%）

## 补充说明

- OHOS 单包 runner 结果：`/storage/Users/currentUser/ohos-test-runs/codex-kbd-2.8.0-kbd-vlock-2.8.0-20260812-r1-conan-20260812-190531-49229`
- 构建命令：`zsh ci/conan/build_and_test.sh archives/k/kbd-vlock/2.8.0`
- 构建摘要：Total 1, Success 1, Failed 0
- L0/L1/L4/L5：pass
- L2：runner 内置 version/help 探针对 PAM 动态库 runenv 不敏感，报告非阻塞 skip；Conan `test_package` 已在 `conanrun` 环境下实际执行 `vlock --version` 与 `vlock --help` 并通过。
- 适配要点：
  - 仅构建上游 kbd 中的 `src/libcommon` 与 `src/vlock`。
  - 增加软件级 `commands.json`，声明 `kbd-vlock` 为命令行工具包。
  - 通过补丁移除 glibc-only `program_invocation_short_name` 依赖。
  - OHOS 下禁用 Linux VT ioctl 路径，当前 tty 模式保留，`--all` 明确返回不支持。
  - 配方内处理 OHOS runner 上 `CONFIG_SHELL`、工具链路径、`pkg-config`/`flex` 探针和 `config.status` 临时目录权限问题。
- issue 编号未在本地项目文件或会话上下文中找到，当前标记为 `TBD`。
