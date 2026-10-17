# opencsg 1.8.2 Path B candidate evidence

本文件记录为什么本次 opencsg 适配可作为 **路径 B（贡献创新 / 知识库扩展）** 候选提交评审。
**最终难度分类由项目评审决定**，本文件只给出证据与边界，不自我认定。

## Claim（主张）

opencsg 的配方本身并不以"新奇"自居：真机 shadow CI 一次通过的构建路径是标准的 CMake +
Conan 适配。路径 B 候选的主张建立在**从真实真机验证中提取出的、可复用的平台知识**上——
其中多条适用于任何图形类（乃至任何运行时加载型）三方库，而不仅是 OpenCSG：

1. 桌面 OpenGL 运行时加载型库在 HarmonyOS 上的完整适配模式（`libGLv4.so` + `libEGL.so`）。
2. 无头 CI 下"核心功能需要上下文"的库如何写出**既可通过 R34/L1e、又不谎报覆盖**的 test_package 契约。
3. 真机隔离 job 里 hnp 工具链不在 PATH 导致的 `cmake: Error 127` 的定位与正确调用惯例。
4. OHOS CMake 缺 `Platform/HarmonyOS.cmake` → 共享库无 SONAME 的**最小复现与平台级判定**。
5. 用 `DT_NEEDED` 断言运行时加载型库未误链系统同名库（R26 自查方法）。
6. 上游 tag 名与版本号不一致时的源码归档选择 + 干净 `.tar.gz` basename。
7. `make jobserver mkfifo: Operation not permitted` 为非致命告警的判据。

## Evidence（证据）

- Task library slot: `opencsg`
- Conan package: `opencsg/1.8.2`（上游版本与 Conan 版本一致，未递增后缀）
- Worktree branch: `feat/opencsg-1.8.2`
- Scope: `archives/o/opencsg/` 及 `knowledge/drafts/opencsg-1.8.2-*`（仅本库直接相关知识）
- 上游仓库: https://github.com/floriankirsch/OpenCSG
- 上游 tag: `opencsg-1-8-2-release`（注意不是 `v1.8.2`）
- Source archive: `https://github.com/floriankirsch/OpenCSG/archive/refs/tags/opencsg-1-8-2-release.tar.gz`
- SHA256: `63c74513f8197ceaef68bd90502c096b64146997d67e0979a82e0e8db2928527`
- 本机前置验证: OHOS SDK clang 15.0.4 交叉编译（aarch64-linux-ohos）通过
- 真机 shadow CI（通过）:
  - 运行目录: `~/ohos-test-runs/codex-opencsg-opencsg-1.8.2-shadow-hnppath-20260911-210449-7932`
  - job: `~/ohos-users/codex/opencsg-1.8.2-shadow-20260911`
  - `Total: 1`, `Success: 1`, `Failed: 0`, exit code `0`
- Gates:
  - `L0_RESULT=pass: all checks passed`
  - `L1_RESULT=pass: test_package executed`
  - `L2_RESULT=skip: no bin/ dir`
  - `L4_RESULT=pass: patches clean`
  - `L5_RESULT=pass: lib/ has content`
  - `L1e: Negative test confirmed — test genuinely depends on opencsg`
- 设备 test_package 输出: 9 项确定性断言 + 2 项运行时探针断言全部 `[ok]`；`test_opencsg: PASS`
- 设备产物: `lib/libopencsg.so`（346560 bytes，ELF 64-bit arm64），
  `DT_NEEDED=[libc++_shared.so, libc.so]`，885 个 OpenCSG 导出符号

## Draft knowledge added（知识草稿，7 对 .kv/.md）

1. `opencsg-1.8.2-ohos-glad-desktop-gl-loader` — 桌面 GL 运行时 dlopen 型库在 OHOS 的适配（旗舰条目）
2. `opencsg-1.8.2-ohos-headless-context-dependent-test-contract` — 无头 CI 真测试契约（通用测试方法论）
3. `opencsg-1.8.2-shadow-ci-isolated-job-hnp-toolchain-path` — 隔离 job hnp 工具链 PATH（CI 基础设施）
4. `opencsg-1.8.2-ohos-cmake-missing-platform-soname` — OHOS CMake 无 SONAME（平台限制，含最小复现）
5. `opencsg-1.8.2-dt-needed-verification-for-runtime-dlopen-libs` — DT_NEEDED 验证法（R26 自查）
6. `opencsg-1.8.2-upstream-tag-name-vs-version-archive-selection` — 源码归档选择（Conan source 通用）
7. `opencsg-1.8.2-make-jobserver-mkfifo-not-permitted` — make jobserver 告警判据（构建环境通用）

## 库内真实适配贡献（非仅知识）

- `patches/0001-glad-ohos-opengl-loader.patch`：给 glad 候选库名追加桌面 GL 入口库
  `libGLv4.so`，并让过程地址助手在 GLX 不可用时回退 `libEGL.so` 的 `eglGetProcAddress`
  （GLX 优先、EGL 兜底）。**POSIX 通用写法，仅用 glad 自带平台宏守卫，不引入 `__OHOS__` 等
  平台宏**（R8 / preflight PF5）。
- `patches/0002-src-CMakeLists-optional-opengl-lookup.patch`：`find_package(OpenGL REQUIRED)` 降为
  可选（目标本不链接 GL；OHOS 无 GL 开发包）。两补丁对其他平台的行为透明（R8）。

## What this does not claim（不主张的内容）

- 不主张 OpenCSG 配方的构建路径本身新奇——它是标准 CMake+Conan 适配。
- 不主张 `render()`（Goldfeather/SCS + FBO/遮挡查询）的真实渲染已在 OHOS 验证；
  该路径需应用侧真实 GL context，本轮未执行。
- 不主张覆盖了纯 GLES 设备的桌面 GL 兼容问题；本方案针对提供 `libGLv4.so` 的 OHOS 设备。
- 不主张 SONAME 缺失已解决——它是设备 CMake 的平台限制（已用最小复现证明），
  本 PR 不做平台级 hack。
- 不主张上游有单元测试被执行——OpenCSG 1.8.2 上游没有单元测试套件，这一点如实记录。

## Reviewer checklist（评审对照）

- [ ] 确认仅包含 opencsg 相关的知识草稿，未改动基础设施目录。
- [ ] 确认 7 对草稿的 `.kv`/`.md` 同stem成对、无模板占位符残留（`knowledge_check.sh` 通过）。
- [ ] 确认真机 shadow CI 门禁 L0/L1/L2/L4/L5 与 L1e 的证据可追溯。
- [ ] 确认上游测试事实：OpenCSG 1.8.2 无单元测试套件，test_package 为消费者补全测试。
- [ ] 判定 7 对草稿是否达到 B 类（贡献创新/知识库扩展）认可标准。
