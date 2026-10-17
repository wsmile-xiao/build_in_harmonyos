## PR 信息

- **三方库名称**：ii
- **上游版本**：2.0
- **上游仓库地址**：https://git.suckless.org/ii
- **适配路径**：路径 B（贡献创新）
- **使用知识库**：知识库扩展草稿 `DRAFT-ii-ohos-native-fifo-integration-test`

## 变更内容

- 新增 `archives/i/ii/2.0/` Conan 配方、源码校验信息、元数据、适配笔记与消费测试。
- 添加 HarmonyOS 沙箱兼容补丁：目标 UID 无 passwd 记录时使用安全的默认 nick 与 `HOME`（无效时 `/tmp`），避免 `getpwuid()` 阻止程序启动。
- 新增 `archives/i/ii/commands.json`。
- 新增 HarmonyOS PC 本机测试，验证 `getpwuid()` fallback 后目标二进制可启动并输出 CLI usage。CI 沙箱禁止 socket bind 和 `mkfifo`（均返回 `EPERM`），因此该用例不模拟 IRC/FIFO 会话。
- 新增路径 B 知识库草稿：`knowledge/drafts/DRAFT-ii-ohos-native-fifo-integration-test.{kv,md}`。
- 上游 tag `2.0`：`236114cf1fa4754da6679f68f01b5ab39553fe7c`；源码包 SHA-256：`4f67afcd208c07939b88aadbf21497a702ad0a07f9b5a6ce861f9f39ffe5425b`。

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 0 | 上游无单元测试 |
| 集成测试 | 0 | 上游无测试套件 |
| 其他测试 | 0 | Makefile 不含 `test`/`check` 目标 |
| **合计** | **0** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------:|-----------|------|
| 单元测试 | 0 | 不变 | |
| 集成测试 | 0 | 不变 | |
| 鸿蒙特有测试 | 1 | 新增 1 | HarmonyOS PC 原生测试：运行目标二进制验证 passwd fallback、CLI usage 与退出状态 |
| **合计** | **1** | **新增 1** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

上游没有测试套件，本 PR 未修改上游测试文件。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

- **补全的测试范围**：新增 1 个 HarmonyOS PC 原生启动测试，覆盖无 passwd 条目时的 fallback、usage 输出与退出状态。
- **补全原因**：上游仅包含客户端程序，没有正式测试框架或测试用例。
- **新增测试文件清单**：`archives/i/ii/2.0/test_package/test_ii.py` — 启动目标二进制并断言 usage 输出和退出状态。

## 验证结果

- 编译状态：前一轮 CI 的 Conan 补丁应用、编译、打包及 CLI 检查通过，后在被沙箱禁止的 `mkfifo` 处失败，该调用已移除。最新一轮未执行包构建，在 worker shell 阶段 `fork failed: out of memory`；当前头待重跑。
- 上游测试用例通过率：0/0（上游无测试用例，不适用百分比）。
- 新增测试用例通过率：当前头 CI 待运行，尚无通过率数据。
- **鸿蒙特有测试**：HarmonyOS PC 原生 ii CLI/passwd fallback 启动检查，等待新头机器人 CI 执行。

## 补充说明

- [x] `conanfile.py` settings 含 `compiler` 与 `build_type`。
- [x] 存在 `archives/i/ii/commands.json`。
- [x] 本 PR 仅新增一个软件包 `ii/2.0`。
- [x] 源码 tag 与官方源码包 SHA-256 已核实。
- 构建系统为上游 POSIX Makefile，使用 Conan `AutotoolsToolchain`；Conan 依赖：无。
