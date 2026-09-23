## PR 信息

- **三方库名称**: socket99
- **上游版本**: 0.2.2
- **上游仓库地址**: https://github.com/silentbicycle/socket99
- **前置依赖关系**: 无 Conan 编译依赖；仅使用 OHOS profile 提供的 Clang/LLVM 工具链。
- **适配路径**: 路径 A（基础适配）+ 路径 B（贡献创新）
- **使用知识库**: E024、E098、E174、E340；新增 `knowledge/drafts/E341-draft-BBEA.{kv,md}`；详细证据见 `archives/s/socket99/0.2.2/reports/path-b-candidate.md`
- **关联 Issue**: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/2561

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| 单元测试 | 0 | 上游没有独立单元测试框架；`test_socket99.c` 提供按角色返回结果的进程入口 |
| 集成测试 | 5 组 / 10 角色 | `test_all` 的 TCP blocking、TCP nonblocking、UDP、Unix stream、Unix datagram 客户端/服务端配对 |
| 其他测试 | 0 | 上游没有 `make check` 目标；真实入口是 `make test` |
| **合计** | **5 组 / 10 角色** | 设备端按角色记录 6 passed、4 skipped，不把 skipped 计为 passed |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------:|-----------:|------|
| 单元测试 | 0 | 不变 | 未新增独立单元测试框架 |
| 集成测试 | 5 组 / 10 角色 | 不变 | OHOS 执行 TCP/UDP 3 组、6 角色；Unix 2 组、4 角色因已复现的 `bind()` 能力限制显式跳过 |
| Conan consumer 测试 | 1 个可执行文件 / 8 个断言 | 新增 | 编译、链接并运行安装后的静态库和公共头文件 |
| 鸿蒙特有测试 | 0 | 不适用 | 本次使用证据绑定的门禁，不伪造 OHOS 专属 socket 能力 |
| **合计** | **5 组上游集成场景 + 1 个 consumer / 8 个新增断言** | **新增 package closure** | 上游角色仍按 6 passed、4 skipped 分开统计 |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改

1. **修改的测试文件**: `test_all`
   - **修改原因**: OHOS 设备在用户可写目录中对 pathname Unix-domain socket 的 `bind()` 仍返回 `Operation not permitted`；该限制已通过未修改 harness 的第一轮运行和独立可写目录复跑定位。
   - **修改内容**: 增加 `SOCKET99_SKIP_UNIX=1` 能力开关，仅在该变量为 `1` 时跳过 Unix stream/datagram 两组；TCP blocking、TCP nonblocking 和 UDP 原有命令保持不变。配方仅在 `settings.os=OHOS` 设置该变量。

`0001-socket99.h.patch` 是公共头文件自包含性修复，不是测试用例修改。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖核心 socket 场景
- [ ] **是**，上游无测试用例，适配后补全了测试

上游虽有 5 组 / 10 角色的网络集成测试，但不验证 Conan 安装布局、公共头文件自包含性或消费者链接。因此新增的 `test_package` 是 package-level 补充验证，不被计作上游测试替代：

- **补充的测试范围**: 编译安装后的 `socket99.h`，链接 `libsocket99.a`，检查 IPv4/UDP 地址提示、矛盾地址配置错误和错误格式化，共 8 个显式 `CHECK`。
- **补充原因**: 上游 harness 验证源码树中的通信角色，不覆盖 Conan 包导出的 include/lib 目录和公共 API 消费闭环。
- **新增测试文件清单**:
  1. `archives/s/socket99/0.2.2/test_package/conanfile.py` — 从 Conan dependency metadata 编译并运行消费者。
  2. `archives/s/socket99/0.2.2/test_package/test_socket99.c` — 8 个真实 API/configuration checks。
  3. `archives/s/socket99/0.2.2/test_package/MANIFEST.yml` — 记录 5 组 / 10 角色的上游范围和 OHOS 跳过边界。

---

## 验证结果

- 编译状态: 通过
- 上游测试用例通过率: 6/10 角色（60%）；另有 4/10 角色显式 skipped，原因是 OHOS 用户可写目录中的 pathname Unix socket `bind()` 为 `Operation not permitted`，不计入通过率
- 新增消费者断言通过率: 8/8（100%）
- 设备构建命令: `conan create "$HOME/ws/wt-socket99-0.2.2/archives/s/socket99/0.2.2" --build="socket99/*" -pr:h="$HOME/ws/build_in_harmonyos/ci/conan/profiles/ohos-aarch64" -pr:b="$HOME/ws/build_in_harmonyos/ci/conan/profiles/ohos-aarch64"`
- 设备结果: Conan 2.29.1、Clang 15.0.4、GNU Make 4.4.1；最终计数复核返回 0
- 证据日志: `$HOME/tmp/socket99-0.2.2-w3-r8-count-fix/conan-create.log`；前两轮失败原因见 `$HOME/tmp/socket99-0.2.2-w3-r1/conan-create.log` 和 `$HOME/tmp/socket99-0.2.2-w3-r2/conan-create.log`，r3/r4 为此前成功复验
- 源码 SHA-256: `657907afc1e2dc42406d257cc032e97f66739c8d8873c424b567a913d3ffc36e`

---

## 知识库扩展说明

- 新增 `knowledge/drafts/E341-draft-BBEA.{kv,md}`，并创建关联 Issue #2561。
- E024/E340 已分别覆盖 OHOS Unix socket 能力限制，E098/E174 已分别覆盖缺少 `install` 工具；E341 的新增价值是将“可写目录复现 → 仅门禁受限测试组 → declared/executed/passed/skipped 分账 → Conan `mkdir/copy` 打包 → 安装后 consumer closure”固化为一个跨库可复用流程。
- 首轮未修改 harness 的上游测试在 TCP/UDP 6 个角色通过，Unix 4 个角色 `bind()` 失败；同一测试程序在 `$HOME/tmp/socket99-0.2.2-upstream-r1` 再现相同错误。
- 第二轮启用测试门禁后，构建与上游支持场景通过，但 `make install` 因设备缺少 `install` 返回 127；最终 `package()` 改用 Conan 原生文件 API，第三轮完整通过。
- Path B 只申请 10 分候选，最终知识条目编号与分值以官方评审为准。

---

## 补充说明

- 任务分支 / PR 源分支: `feat/socket99-0.2.2`
- 目标分支: `OpenHarmonyPCDeveloper/build_in_harmonyos:main`
- 代码路径: `archives/s/socket99/0.2.2`
- 关联 Issue: `https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/2561`
- 版本级 manifest 状态为 `built`；尚未执行 release upload，不标记 `published`。
- `0001-socket99.h.patch` 是可移植公共头修复；`0002-test_all.patch` 是仅由 OHOS 配方环境变量触发的测试能力门禁；非 OHOS 构建仍运行完整上游 Unix 测试。
- 远端验证后已删除 Conan test consumer 产生的未跟踪可执行文件；本地 worktree 未运行 macOS Conan/OHOS 构建。
