- **三方库名称**：jool-tools
- **上游版本**：4.1.14
- **上游仓库地址**：https://github.com/NICMx/Jool
- **适配路径**：路径 A（基础适配）
- **使用知识库**：E119（OHOS netlink/socket 头冲突）、E236（libtool archive 搜索路径）、R15（Autotools 主机 triplet）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 官方 v4.1.14 release 未声明 `TESTS` 或 `check_PROGRAMS` |
| 集成测试 | 0 | release tarball 无 `test/` 测试目录 |
| 其他测试 | 0 | 无其他上游测试入口 |
| **合计** | **0** | `make check` 可执行，但上游没有测试用例 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | - |
| 集成测试 | 0 | 不变 | - |
| 其他测试 | 23 | 新增 23 | 三个交付程序的执行权限、ELF、版本/帮助输出、`joold` 参数错误契约及 OHOS netlink 降级路径 |
| 鸿蒙特有测试 | 3 | 新增 3 | 三个程序均检查目标 ELF `e_machine=183`（AArch64） |
| **合计** | **26** | **+26** | `test_package/test_cli.sh` 在 OHOS CI 上共 26 项断言 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，未新增测试
- [x] **是**，上游无测试用例，适配后补全了测试

- **补全的测试范围**：实际交付的 `jool`、`jool_siit`、`joold` CLI 行为、HarmonyOS PC AArch64 ELF 目标 ABI，以及缺少内核模块时的 netlink 降级路径。
- **补全原因**：上游 release 未提供测试套件，需覆盖交付二进制及目标架构。
- **新增测试文件**：`test_package/test_cli.sh` — OHOS CI 26 项消费者侧断言。

## 验证结果

- 编译状态：等待 GitCode CI
- 上游测试用例通过率：0/0（无上游测试用例）
- 新增测试用例通过率：CI 待运行（26 项）

## 补充说明

- 构建官方 release tarball 的用户态 `jool`、`jool_siit`、`joold`；依赖 `libnl/3.11.0` 和 musl 所需的 `argp-standalone/1.5.0`。
- `--with-xtables=no` 禁用可选 iptables 扩展；内核模块不在此 userspace 工具包的交付范围内。
- OHOS CI 首轮发现上游 `configure` 的 `umask 077` 临时目录在 HMDFS 下不可写（`subs1.awk: Permission denied`）；新增补丁只在 OHOS 应用，将临时目录 umask 设为 `022`，Linux 构建继续使用上游默认行为。
