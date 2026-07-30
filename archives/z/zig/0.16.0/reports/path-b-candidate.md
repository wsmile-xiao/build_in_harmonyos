# zig 0.16.0 Path B Candidate

## 申请信息

- 申请人账号：gcw_hL6s3dcK
- 队伍名称：33号远征队
- 申请日期：2026/07/29
- 库名称：zig
- 版本：0.16.0
- Issue：https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/1562
- PR：https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/3374
- 当前路径：路径 A（基础适配） + 路径 B（贡献创新，候选，最终以官方审核为准）

## 路径 B 申请理由

Zig 不是普通运行时库，而是后续 Zig 生态三方库的构建工具链前置依赖。HarmonyOS 真机对未签名 ELF 的执行限制会同时影响三类 Zig 产物：

1. 官方 aarch64 Linux Zig ELF 本身。
2. `zig build` 自动生成的 `.zig-cache/o/.../build` build runner。
3. `zig build run/test` 生成并立即执行的测试或应用 ELF。

仅签名打包后的 `bin/zig` 只能让 `zig version` 工作，不能保证 downstream Zig-based 包使用 `zig build` 时可执行。此前 OHOS 上游全量测试尝试在进入测试矩阵前失败，错误为 `failed to spawn build runner .zig-cache/o/.../build: AccessDenied`，证明这是会影响一类 Zig 构建工作流的通用问题。

本 PR 在基础 Zig Conan tool package 之外新增了可复用处理：

1. OHOS 包内将官方 Zig ELF 保留为 `bin/zig-real`，并在 `package()` 中自签。
2. OHOS 包内提供 `bin/zig` wrapper，下游仍从 PATH 调用 `zig`，无需改命令名。
3. wrapper 捕获 `AccessDenied` / `Permission denied` / `failed to spawn build runner`，自动调用 `zig-ohos-sign-generated` 签名 `.zig-cache`、`zig-cache`、`zig-out` 中的可执行 ELF，并重试。
4. 包内提供可单独复用的 `zig-ohos-sign-generated [ROOT_OR_FILE ...]`，便于下游 recipe 在特殊构建步骤后主动补签。
5. OHOS 包装阶段窄范围修补 Zig 0.16.0 标准库 `Io/Threaded.zig` 中 `copy_file_range` / `sendfile` 的 `OVERFLOW => errnoBug` 分支，改为 `error.Unimplemented`，让 Zig 既有普通读写 fallback 接管，避免 `zig build install` 在 HarmonyOS 文件系统上 panic。
6. test_package 从简单 `zig build-exe` 升级为 `zig build run install --summary all`，覆盖 build runner 生成、缓存可执行文件运行、install 产物复制三段真实 Zig build 工作流。

## 证据

最终 OHOS runner：

- RUN_DIR：`/storage/Users/currentUser/ohos-test-runs/codex-zig-zig-0.16.0-b-wrapper-conan-final2-20260729-134856-64268`
- 退出码：0
- L0/L1/L2/L4/L5：全部通过
- 下载源：`https://zig.linus.dev/zig/0.16.0/zig-aarch64-linux-0.16.0.tar.xz`
- 包 ID：`876049f3ae10a4560da345bb02378e03e212bc8c`

关键日志片段归纳：

- 首次 `zig build run install` 触发 `failed to spawn build runner .zig-cache/o/.../build: AccessDenied`。
- wrapper 自动补签并重试后进入 build runner，随后又捕获 generated `smoke` 执行 `AccessDenied`。
- 第二轮补签后最终 `Build Summary: 5/5 steps succeeded`，`run success` 和 `install success` 同时通过。
- CI 最终报告 `Success: 1, Failed: 0`。

本机 Windows 验证：

- `conan create . --user=ohpcd --channel=stable --build=missing` 通过。
- `test_package` 执行 `zig build run install --summary all -Doptimize=ReleaseSmall`，`Build Summary: 5/5 steps succeeded`。
- Windows 包使用 mirror-first `https://zig.linus.dev/zig/0.16.0/zig-x86_64-windows-0.16.0.zip`，sha256 仍为官方值。

上游全量测试尝试：

- Windows 上游全量入口已执行，结果为 `6686/7691 steps succeeded`，`108372/111213 tests passed`，失败主要为 Windows host/target matrix 差异。
- OHOS 上游全量入口此前因 generated build runner 未签名失败，本轮 wrapper 正是针对该通用失败点进行复用化处理。

## 复用范围

下游 Zig-based recipe 通常只需要：

```python
self.tool_requires("zig/0.16.0")
```

随后继续调用 `zig build` / `zig build run` / `zig build test`。若下游有特殊步骤生成执行文件，也可显式调用：

```sh
zig-ohos-sign-generated .zig-cache zig-out
```

该能力优先服务 `minizign/0.1.13` 这类声明 `minimum_zig_version = "0.16.0"` 的 Zig 构建系统包，避免每个下游库重复实现 HarmonyOS generated ELF 签名逻辑。

## 已知限制

- 本 PR 不声明 Zig 上游全量测试在 OHOS 100% 通过，也不申请 Path C。
- wrapper 以重试方式处理 Zig 生成物签名，若下游构建系统在非标准目录生成并立即执行 ELF，可能需要额外设置 `ZIG_OHOS_SIGN_ROOTS` 或显式调用 `zig-ohos-sign-generated`。
- Zig std fallback 修补仅应用于 OHOS 包内官方分发文件，不改上游源码仓库，不影响 Windows/Linux 包。
