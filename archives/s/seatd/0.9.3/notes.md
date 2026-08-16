# seatd 0.9.3 HarmonyOS 适配记录

## 当前状态

- issue: `2146`
- 分支: `feat/seatd-0.9.3-2146`
- 状态: `built`，单包 shadow CI 在 HarmonyOS aarch64 真机通过
- 修改范围: `archives/s/seatd/0.9.3/`，以及与 seatd 直接相关的
  `knowledge/drafts/DRAFT-seatd-noop-backend-validation-2146.{kv,md}` 草稿

## 上游与构建系统

- 上游仓库: <https://git.sr.ht/~kennylevinsen/seatd>
- 版本标签: `0.9.3`
- 标签提交: `daa8196e10b180b8b0caeafa8e5f860eb1bd6706`
- 构建系统: Meson `>= 0.60.0`
- 主要产物: `libseat.a`、`seatd`、`seatd-launch`
- 许可证: MIT

源码使用维护者名下的 GitHub 官方镜像归档。已通过官方 SourceHut Git 仓库浅克隆
确认标签和提交，并通过 GitHub codeload 端点下载 42086 字节归档，独立复算 SHA256
为 `302564d54d8e28191fadfd734f2675ecb0c9e0615a58011b89ef15dfa4dbaa96`。

## W0 依赖结论

默认 OHOS 配置没有需要从 Conan 制品仓解析的三方库依赖：

- 必需: libc；Meson 还探测系统 `librt`，不构成 Conan 包依赖。
- 可选: `libsystemd` / `libelogind`，仅 logind 后端需要，OHOS 配方显式禁用。
- 可选: `scdoc >= 1.9.7`，仅生成 man page，配方显式禁用。
- 构建工具: Meson、Ninja，由 worker 工具链提供，不纳入运行时依赖。

因此 W0 通过，不需要拆分依赖库 issue/PR。

## OHOS 配置

- OHOS 强制静态 `libseat`，保留 `seatd` 与 `seatd-launch`。
- 保留 seatd 后端，关闭 logind、builtin、man page 和 examples。
- 上游默认 `warning_level=3` 且 `werror=true`。OHOS SDK 的
  `CMSG_NXTHDR()` 宏会在 `common/connection.c` 展开处触发
  `-Wsign-compare`，因此仅在 OHOS 设置 `werror=false`，不修改上游源码。
- 若 OHOS profile 只声明 clang，主配方和 test_package 都从同目录补入
  `llvm-ar` 和 `llvm-ranlib` 到 Conan 生成的 Meson native file。

## 上游测试与裁剪

上游在顶层 `meson.build` 中定义三项测试：

| 测试 | 结果 | 说明 |
|---|---|---|
| `linked_list` | 通过 | 真机耗时约 0.05 秒 |
| `connection` | 通过 | socketpair、消息编解码与 fd 传递，真机耗时约 0.04 秒 |
| `poller` | 默认跳过 | 现有 OHOS aarch64 记录显示会无限阻塞 |

`poller` 没有被删除或修改。后续真机复核必须单独加外部超时，避免占用全局设备锁。

## test_package

消费者测试使用 Meson，避免依赖设备未安装的 CMake 和 pkg-config。Conan 将已安装
包的 include/lib 绝对路径传给 Meson，Meson 再用 clang 查找并静态链接 `libseat`。

测试通过始终编译的 `noop` 后端实质调用 `libseat` 公共 API，共 15 条断言：

- 非法 listener 与未知 backend 的错误契约和日志回调；
- `open_seat`、`seat_name`、`get_fd`、两次 `dispatch`；
- enable 回调仅触发一次；
- 对真实临时文件执行 `open_device` / `close_device`；
- 缺失设备返回 `ENOENT`；
- `close_seat` 完成生命周期。

真机结果为 `15/15 checks passed`。CI 的 L1e 破坏性负测还移走 bin/lib/include，确认
测试确实依赖 seatd 包内容，而不是误用系统安装。

## Shadow CI

- 设备: HarmonyOS aarch64，clang 15.0.4，Meson 1.11.1，Ninja 1.13.0
- 最终 RUN_ID:
  `codex-seatd-seatd-0.9.3-2146-20260814-codex-conan-20260814-150253-44478`
- 时间: `2026-08-14 15:02:54 +0800` 至 `15:04:25 +0800`
- 退出码: `0`
- 构建: 34 个上游编译/链接目标完成，静态库、两个 CLI、头文件和 pkg-config 文件完成打包
- L0: pass
- L1: pass，上游测试 2/2，consumer 15/15，破坏性负测通过
- L2: skip，`seatd` 和 `seatd-launch` 不接受 `--version/--help`，按 CI 规则非阻塞
- L4: pass，无补丁
- L5: pass，`bin/` 有产物

完整迭代与证据哈希见 `reports/shadow-ci-2146.md`。

## 路径 B 知识草稿

路径 B 候选材料已成对写入：

- `knowledge/drafts/DRAFT-seatd-noop-backend-validation-2146.md`
- `knowledge/drafts/DRAFT-seatd-noop-backend-validation-2146.kv`

草稿沉淀“通过上游 noop backend 在无特权环境验证 seat-management 公共 API 的事件与
设备生命周期”的方法，并与 E285 音频 Null/loopback 及 E321 测试专用 mock 的适用边界
区分。草稿不修改正式 graph/doc/index，不预占正式 E 编号；是否提升及路径 B 最终认定以
知识库维护者和赛事评审为准。详细举证见 `reports/path-b-candidate.md`。

## 已知边界

- `poller` 仍未在本轮默认任务中运行，必须用外部 30 秒超时单独复核。
- `seatd` 守护进程实际管理 `/dev/input`/DRM 设备仍需要权限策略与硬件工作流验证；
  test_package 只验证可在沙箱中稳定运行的 libseat API。
- L2 的两个 CLI 探测失败不是构建失败；上游程序没有标准 version/help 接口。

## 复现命令

单包 CI：

```sh
CI_PACKAGES="archives/s/seatd/0.9.3" zsh ci/conan/build_and_test.sh
```

隔离运行目录单独复核 `poller`：

```sh
timeout 30s meson test -v --print-errorlogs -C "$BUILD_DIR" poller
```
