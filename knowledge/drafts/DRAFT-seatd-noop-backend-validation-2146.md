# DRAFT-seatd-noop-backend-validation-2146 - 无特权 seat-management 公共 API 验证

> **Contributor**: xuguowei | **Status**: VERIFIED DRAFT | **Updated**: 2026-08-14
> **Source event**: seatd 0.9.3, issue #2146, PR #5307

## 知识类型与提升边界

本条目是路径 B 知识库扩展草稿，不预占正式 E 编号。它只进入
`knowledge/drafts/**`，不修改 `knowledge/graph/`、`knowledge/doc/`、索引或运维规则，
也不声称已经 promote；是否提升及最终路径分类由知识库维护者和赛事评审决定。

## 适用场景

适用于具有以下特征的系统库：

- 生产 backend 依赖守护进程、Unix socket、特权服务或真实设备节点；
- 上游同时提供始终可用的 null/noop backend；
- CI/test_package 以普通用户运行，不能稳定获得生产设备与权限；
- 仍需验证已安装包的公共 API、事件回调和资源生命周期，而不只是链接 smoke test。

seatd 的生产路径需要 seatd socket 或 logind，并最终涉及 DRM/input 设备权限。直接在
共享真机上启动守护进程或访问真实设备，会把测试结果绑定到系统状态和权限策略。

## 症状与根因

无特权环境中直接选择生产 backend 时，常见现象是无法连接 seatd socket、找不到
logind backend、访问设备节点失败，或 consumer 在 open seat 阶段即退出。根因不是
`libseat` 公共 API 无法编译，而是生产 backend 的运行前置条件不属于单包 CI 的稳定契约。

仅构建和链接一个 consumer 也不充分：它不能证明 backend 选择、pollable fd、dispatch
回调、设备 open/close、错误码和资源清理在目标系统上实际工作。

## 推荐方法

### 1. 显式固定上游 noop backend

通过 `LIBSEAT_BACKEND=noop` 显式选择上游已有且始终编译的 noop backend。必须显式设置，
不能依赖自动探测顺序，否则测试可能在不同设备上走到 seatd 或 logind。

### 2. 验证公共 API 的完整生命周期

consumer 至少覆盖：

1. `libseat_open_seat` 成功并返回预期 seat name；
2. `libseat_get_fd` 返回可轮询描述符；
3. 第一次非阻塞 `libseat_dispatch` 触发一次 enable callback；
4. 第二次 dispatch 不重复触发 callback；
5. `libseat_close_seat` 完成清理。

### 3. 用临时普通文件验证设备句柄契约

在当前可写测试目录创建临时普通文件，将它交给 `libseat_open_device`，要求返回有效
device id 和 fd，再调用 `libseat_close_device`。这样可以验证安装包中的设备 API 和 fd
生命周期，同时不访问 `/dev/input`、DRM 或其他真实节点。

补充一个确定不存在的路径，要求返回 `-1` 且 `errno == ENOENT`，避免只覆盖成功路径。

### 4. 覆盖配置和错误契约

验证空 listener、不完整 callback、未知 backend、错误日志回调等行为。错误场景必须检查
返回值和 errno，不能只匹配一段易变化的日志文本。

### 5. 证明 consumer 使用的是被测包

除正向运行外，执行包内容破坏性负测：临时移走被测包的 `include/lib/bin` 后重新构建或
运行 consumer，要求失败；恢复后再验证通过。该负测用于排除误链接系统安装或缓存产物。

### 6. 分层记录测试结果

必须分别记录：

- 实际执行的上游测试及通过率；
- noop consumer 的断言数和通过率；
- 因超时、权限或硬件条件未执行的项目；
- 真实生产 backend 尚未覆盖的权限与设备行为。

noop consumer 是无特权替代验证，不等同于真实 seatd daemon/logind/DRM/input 验证。

## 与已有知识的差异

- 正式条目 E285 处理 OpenAL 音频库的 Null/loopback：重点是关闭外部音频 backend、创建
  音频 context 并离线渲染。本草稿处理 seat-management 库，新增 Unix socket/特权服务
  边界、pollable event fd、enable callback 次数、设备 fd/device id 生命周期和 errno 契约。
- `E321-draft-qbootctl-a-b-slot-mock-backend` 为没有注入点的硬件 CLI 新增编译期测试专用
  mock，并严格隔离生产二进制。本草稿不修改上游源码、不新增 mock；它复用上游正式提供
  的 noop backend，并重点验证已安装共享 API 的消费契约。

因此，可复用的新增知识不是“null/noop backend 存在”这一泛化事实，而是针对特权
seat-management API 的显式 backend 选择、事件/设备双生命周期、errno 覆盖、包依赖负测
以及测试证据分层组合。

## 禁止做法

- 不要在共享 CI 中启动或重配置真实 seatd 守护进程。
- 不要访问、写入或伪造 `/dev/input`、DRM、logind 等真实生产资源。
- 不要把 noop 验证写成真实 backend 已通过。
- 不要把跳过或超时的上游测试计为 pass。
- 不要为通过 consumer 而修改上游 noop backend 的生产语义。
- 不要把缺 CMake/pkg-config 或补 `llvm-ar`/`llvm-ranlib` 等常规环境兼容作为本条路径 B
  的主要创新证据。

## 已验证示例

seatd 0.9.3 的 Conan `test_package` 在 HarmonyOS aarch64 真机通过 15/15 项断言，覆盖
listener 参数、未知 backend、日志回调、seat open/name/fd、两次 dispatch、enable callback、
临时文件设备 open/close、缺失设备 `ENOENT` 和 seat close。

上游 `linked_list`、`connection` 实际执行 2/2 通过；`poller` 因已有无限阻塞证据保留但
未进入默认任务。官方 PR CI #25154 的 Conan test_package、L0、L1 均通过。

复现入口：

```sh
CI_PACKAGES="archives/s/seatd/0.9.3" zsh ci/conan/build_and_test.sh
```

真机 shadow RUN_ID：
`codex-seatd-seatd-0.9.3-2146-20260814-codex-conan-20260814-150253-44478`。

## 证据来源

- `archives/s/seatd/0.9.3/notes.md`
- `archives/s/seatd/0.9.3/test_package/test_package.c`
- `archives/s/seatd/0.9.3/reports/path-b-candidate.md`
- `archives/s/seatd/0.9.3/reports/shadow-ci-2146.md`
- AtomGit PR #5307 / CI #25154
