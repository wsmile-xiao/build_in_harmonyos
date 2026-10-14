## PR 信息

- **三方库名称**：libsigrok
- **上游版本**：0.5.2
- **上游仓库地址**：https://sigrok.org/wiki/Libsigrok
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新）
- **使用知识库**：本 PR 的 E14849 草稿；已查重四处知识范围

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 76 | `tests/main` 中 12 套 Check suite 共 76 个用例 |
| 集成测试 | 0 | 无另行注册的集成入口 |
| 其他测试 | 0 | 无其他注册测试 |
| **合计** | **76** | `make check` 的真实 Check 用例数；不是 1 个测试 ELF |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|---------------:|------------|------|
| 单元测试 | 76 | 不变 | 全部上游 Check 用例真机 76/76 |
| 集成测试 | 0 | 不变 | 无注册入口 |
| 鸿蒙特有测试 | 1 | +1 | 已安装包 C API 版本、上下文和驱动枚举 |
| **合计** | **77** | **+1** | 上游 76/76，消费者 1/1 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

配方为 Check 0.15 的 printf 格式检查修正上游测试输出的格式参数，不删除用例、不修改预期值或放宽断言；76 个原始 Check 用例均保留。使用上游公开 `--without-libusb` 关闭本机不可用的可选 USB 后端，并如实报告功能边界。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试

另增 `test_package/consumer.c` 验证安装包公开 C API。

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：76/76（100%）
- 新增测试用例通过率：1/1（100%）

- 本轮目标机 W3 `libsigrok-w3-20261010T105000Z` 12 阶段通过，干净 Conan RC0、上游76/76及消费者1/1；原始日志 SHA-256 `7580a82df2b5d6bc8fe8b902a4fcf87732dbf0a248335868534e486d15ff25fe`。
- CI #80119 首错为 config.status 临时目录创建权限；配方精确修复 primary/fallback，在任务 TMPDIR 排他 mkdir 避免 mktemp 固定0700，保留清理、错误和全部测试。现有知识草稿补充阶段区分与创建工具固定权限边界，不用继续关闭驱动或削减测试来绕过。
- CI #70527 的 worker 缺少新版 `config.sub`；回退路径只修本轮构建副本，已由独立测试 `BUNDLED_CONFIG_SUB_FALLBACK_PASS` 覆盖。该失败发生在 configure 前，非源码下载问题。
- B 类增量：可选硬件后端全局初始化会阻断无关 Check 测试；以官方 feature gate 精确缩小功能范围，同时保持测试分母完整。

---

## 补充说明

- 关联 Issue：#3736
- 队伍名称：诶，云朵
- 申请人显示标识：2501_91199785
- 源分支：OpenHarmonyPCDeveloper:feat/libsigrok-0.5.2
- 目标分支：OpenHarmonyPCDeveloper/build_in_harmonyos:main
- 赛事依赖任务：#14849，已领取；HD1–HD4 均不匹配，按路径 A+B 申报。
- 限制：目标机无 `/dev/bus/usb`；此配方不交付 USB 采集后端，不能声称硬件采集通过。
- 发布：合并后按平台要求执行 `/release`，将制品发布至 ohpcd；目前尚未发布。


### 2026-10-13 当前 CI 修复

A consumer launched by upstream make check needs the uninstalled producer shared-library directory, not only published dependency directories. Add the own build .libs provider to the exact subprocess environment and sign own real shared ELFs before running the unchanged registered tests.

当前真机事务 `libsigrok-ci-repair-w3-20261013-r2`：12阶段和释放 PASS，官方本地CI子步骤 exit0；原始CI日志 SHA256 `0d9c940608577e4d33601684beeab98a5e644d2e48c5037e78c3f9b22117862d`。上游 76 项和消费者 1 程序的声明与断言未减少。配套草稿补充上述可复用边界。完整finish旧归档/格式/就绪标记失败保留，不宣称整个finish RC0；比赛worker CI、最新AI检视、审核和发布仍需针对修复提交确认。


### 2026-10-14 当前 CI 修复

Signing must be idempotent on the task-owned build copy: inspect existing ELF sections, remove an old .codesign only from that disposable copy, sign the copy, require a resulting .codesign, and atomically replace the owned original only after success. Restore the process umask and clean siblings on failure.

当前真机事务 `libsigrok-ci-repair-w3-20261013-r101`：12阶段和释放 PASS，官方本地CI子步骤 exit0；原始CI日志 SHA256 `5bad284736bfa29acc7a734fe365c6fd407e8b5a332f23a2798c5599b1c8a036`。上游 76 项和消费者 1 程序的声明与断言未减少。配套草稿补充上述可复用边界。完整finish旧归档/格式/就绪标记失败保留，不宣称整个finish RC0；比赛worker CI、最新AI检视、审核和发布仍需针对修复提交确认。
