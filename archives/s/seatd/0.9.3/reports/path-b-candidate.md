# seatd 0.9.3 路径 B 候选举证

## 结论

本适配首先完成路径 A 的 Conan 配方、产物打包、上游测试和 consumer 验证。在此基础上，
申请将“无特权 seat-management 公共 API 验证方法”作为路径 B（贡献创新）候选材料。

此处只提出候选，不预先宣称已经获得路径 B 认定；最终分类以赛事评审为准。

## 路径 A 基线

- seatd 0.9.3 在 HarmonyOS aarch64 真机完成源码构建和 Conan 打包。
- 产物包含 `libseat.a`、`libseat.h`、`libseat.pc`、`seatd` 和 `seatd-launch`。
- 上游 `linked_list`、`connection` 两个测试目标执行并通过；`poller` 因已有无限阻塞
  证据保留但不进入默认任务。
- shadow CI 的 L0、L1、L4、L5 均通过，L2 因上游 CLI 不支持标准
  `--version/--help` 而按规则非阻塞跳过。

以上内容属于基础适配，不作为路径 B 的主要依据。

## 路径 B 候选贡献

### 问题

seatd 的典型运行路径依赖守护进程、Unix socket、设备节点以及 DRM/input 权限。直接把
这些条件作为 consumer 测试前置，会使单包 CI 依赖设备权限和系统状态，难以稳定复现；
只做静态链接 smoke test 又无法证明公共 API 的事件与设备生命周期可用。

### 可复用方法

本适配把上游始终编译的 `noop` 后端用作无特权替代路径，并形成以下验证闭环：

1. 通过 `LIBSEAT_BACKEND=noop` 显式选择后端，避免测试结果受设备环境自动探测影响。
2. 用公共 API 完成 open、seat name、pollable fd、两次 dispatch、enable callback 和 close
   的完整事件生命周期验证。
3. 用真实临时普通文件执行 `open_device` / `close_device`，验证描述符和 device id 契约，
   同时避免依赖 `/dev/input` 或 DRM 节点。
4. 覆盖空 listener、缺失 callback、未知 backend、日志回调和缺失设备 `ENOENT` 等错误契约。
5. 使用 L1 破坏性负测移走包内 `bin/lib/include` 后重跑，证明 consumer 没有误链接系统安装。
6. 将上游测试、替代 consumer 测试和未执行项分别统计，避免以 noop 验证冒充真实守护进程验证。

这种方法可复用于“核心 API 可由内置 null/noop backend 驱动，但真实后端依赖特权服务、
硬件或设备节点”的三方库：先验证稳定、确定性的公共 API 契约，再把真实设备验证保留为
单独的权限与硬件测试层。

### 验证覆盖

`test_package` 在真机运行 1 个 consumer 可执行文件，共执行 15 项断言：

1. 空 listener 返回 `EINVAL`。
2. 缺少 enable callback 的 listener 返回 `EINVAL`。
3. 未知 backend 返回 `EINVAL`。
4. backend 错误到达自定义日志回调。
5. noop backend 成功打开 seat。
6. seat name 为 `seat0`。
7. seat 暴露可轮询描述符。
8. 第一次非阻塞 dispatch 成功。
9. 第一次 dispatch 只触发一次 enable callback。
10. 第二次 dispatch 不重复触发 enable callback。
11. 临时设备文件成功创建。
12. `open_device` 返回有效 device id 和描述符。
13. `close_device` 成功。
14. 缺失设备返回 `ENOENT`。
15. `close_seat` 成功。

真机结果为 `15/15 checks passed`。

## 不纳入路径 B 的内容

- 设备缺少 CMake、pkg-config，以及 Meson native file 需要补入 `llvm-ar` / `llvm-ranlib`
  属于常规构建环境兼容，不作为贡献创新证据。
- noop backend 是上游已有能力，本适配的候选贡献是可复现的验证方法、覆盖设计和证据分层，
  不是声称新增了 backend。
- 本轮没有修改 seatd 上游源码，也没有修改上游测试。
- 本轮没有验证真实 seatd 守护进程管理 `/dev/input`/DRM 的权限行为。
- `poller` 未在默认任务执行，因此不能声称上游测试 3/3 全部通过。
- 本材料不申请路径 C（高难度库）认定。

## 证据索引

- 知识草稿：`knowledge/drafts/DRAFT-seatd-noop-backend-validation-2146.md`
- 图谱草稿：`knowledge/drafts/DRAFT-seatd-noop-backend-validation-2146.kv`
- 草稿状态：不预占正式 E 编号，不修改正式 graph/doc/index，不声称已经 promote
- 配方与边界说明：`archives/s/seatd/0.9.3/notes.md`
- consumer 源码：`archives/s/seatd/0.9.3/test_package/test_package.c`
- 本机前置验证：`archives/s/seatd/0.9.3/reports/local-validation.md`
- 真机报告：`archives/s/seatd/0.9.3/reports/shadow-ci-2146.md`
- 最终 RUN_ID：
  `codex-seatd-seatd-0.9.3-2146-20260814-codex-conan-20260814-150253-44478`
- runner stdout SHA-256：
  `4a4ba8fd97fd7f03d585d5064cf0596971ed48f9769fd100902051940df08615`
- Conan build log SHA-256：
  `a4da1cd3c43842988d5e2cf01a6a5327afcc74f1e641dfd2d8b5424ebcc3467c`
