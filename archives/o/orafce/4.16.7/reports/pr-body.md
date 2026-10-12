# orafce 4.16.7 OHOS PC (aarch64) 适配 PR

- **三方库名称**：orafce
- **上游版本**：4.16.7（上游 tag `VERSION_4_16_7`）
- **上游仓库地址**：https://github.com/orafce/orafce
- **适配路径**：路径 A（基础适配）——纯 Conan 打包/移植，未改动上游源码（无 patches）
- **使用知识库**：ohos-conan-finish-local-env、ohos-conan-test-hang、ohos-conan-fork-pr-submit

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | orafce 无独立单元测试框架 |
| 集成测试 | 18 | pg_regress 回归套件（需运行 PostgreSQL 服务端）：init(1) + 功能(12) + 会话并发(5：2 pipe + 3 alert) |
| 其他测试 | 0 | — |
| **合计** | **18** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | |
| 集成测试 | 19 | +1 | 新增鸿蒙特有 harmonyos_feasibility |
| 鸿蒙特有测试 | 1 | 新增 | 加载扩展 + 验证 Oracle 兼容函数（add_months / nvl / decode / to_date 等） |
| **合计** | **19** | **+1** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改任何上游测试逻辑 / SQL / 期望值原文。
- [ ] **是**

> 说明：仅新增 musl 平台候选期望文件 `test_package/dbms_random_4.out`（见下方补全说明），不改动上游既有测试文件。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无针对鸿蒙平台的验证用例，适配后补全了测试（请在下方说明）

> 补全范围与原因：
> - **新增鸿蒙特有端到端测试 `harmonyos_feasibility`**（.sql + .out）：上游无针对鸿蒙平台的验证用例；本用例加载 orafce 扩展并校验 Oracle 兼容函数可正确执行，作为平台可行性门禁。
> - **新增 musl 平台候选期望文件 `dbms_random_4.out`**：上游 `dbms_random` 用例提供 4 个 glibc 候选期望，但 OHOS 使用 musl libc，`random()` 序列与 glibc 不同；musl 下序列确定（同 seed 同输出，已两次 psql 运行验证一致），故补一个 musl 候选期望文件，使既有 `dbms_random` 用例在 OHOS 上确定性通过。
>
> 新增测试文件清单：
> 1. `test_package/harmonyos_feasibility.sql` — 鸿蒙可行性测试脚本
> 2. `test_package/harmonyos_feasibility.out` — 对应期望输出
> 3. `test_package/dbms_random_4.out` — musl 平台 dbms_random 候选期望
> 4. `test_package/test_orafce.c` — 消费者可行性 smoke（clang 编译 + `self.run` 校验 `lib/orafce.so` 为有效 ELF）

## 验证结果

- 编译状态：通过（`conan create` 退出码 0，`Package '...' created`）
- 上游测试用例通过率：18/18（100%）
- 新增测试用例通过率：1/1（100%，harmonyos_feasibility）；musl 候选 dbms_random 随既有用例一并 19/19 全过
- 适配后整体：pg_regress **19/19（100%）**，含鸿蒙特有用例

## 补充说明

- 依赖 `postgresql/18.3`（OHOS aarch64，已发布，R36 满足）；本包首次发布（R37 通过）。
- 适配要点：PGXS 构建绕过 Conan `self.run()` 启动器污染；PG 集群建于 `_TMPFS_ROOT`（`/data/storage/el2/base`，uid 正确）避免 initdb ownership 报错；`LD_LIBRARY_PATH` 增加 `pg_config --libdir` 解决 `libpq.so.5` 加载失败；扩展安装进 postgresql 包真实 `share/postgresql/extension` 与 `lib/postgresql`（OHOS PG 构建忽略 `extension_control_path`/`dynamic_library_path`）。
- 本 PR 仅含 `orafce/4.16.7` 当前版本文件（11 个包源文件 + 3 个报告），不含任何依赖库（postgresql）或其他软件/版本文件，不含原始构建日志（conan-create.log / w3-local-ci.log 不随 PR 提交，原始日志本地留存）。
- PF0 / PF9 为已知误报（fork head 前缀 / 软件级三件套所在层），已离线评估 PF1–PF8 真实通过。
