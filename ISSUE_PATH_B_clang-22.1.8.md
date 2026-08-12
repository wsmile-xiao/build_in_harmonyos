【申请人账号】yanjiaxin
【队伍名称】哈哈哈哈哈
【申请日期】2026/08/04
【库名称】clang 22.1.8（中等难度工具链库）

## 关联 PR

- PR：!3868
- PR 链接：https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/3868
- 分支信息：feat/clang-22.1.8 → main
- 当前提交：dd820cd3（含路径 B 知识草稿 DRAFT-clang-ohos-native-llvm-toolchain；此前含动态 SDK/clang_rt 发现、规则 4 豁免、open-mpi 超时恢复、单值官方 URL 等）
- PR 状态：开放中

## 申请路径 B 的理由

clang 属**中等难度**三方库/工具链：上游 `check-clang` / `check-llvm` 等 lit + unittest 规模约 **3–4 万**量级。若仅按路径 A「基础适配」申报，难以体现这类大规模工具链在 OHOS 真机上的组合适配经验沉淀价值；导师亦建议按**路径 B**推进。

本 PR 不是孤立 bug / 单个编译 patch，而是在 HarmonyOS PC 真机上从 llvm-project 原生构建可分发 clang 工具链时，必须同时满足的一组可跨库复用组合方案：

1. **平台识别组合**：LLVM `config.guess`/`get_host_triple` 不认 `uname=HarmonyOS`；CMake 缺 `Platform/HarmonyOS`。正确做法是 stub 输出 `aarch64-unknown-linux-ohos` + 注入 `Platform/HarmonyOS.cmake`（`include(Platform/Linux)`），且**不设** `CMAKE_SYSTEM_NAME`，否则 tblgen 被拖进交叉编译失败。
2. **自包含运行时组合**：仅 `-DLLVM_ENABLE_PROJECTS=clang` 时安装树无 crt/builtins；须从 OHOS SDK **动态发现** `lib/clang/<ver>/lib/aarch64-linux-ohos` 与 `libc++_shared.so` 捆绑进包，缺失则 `ConanException`（禁止静默空壳工具链）。
3. **体积与安全组合**：`LLVM_BUILD_LLVM_DYLIB`/`LINK` 绕过制品仓单文件上限；`binary-sign-tool` 满足 OHOS XPM 对 ELF / `.so` 的签名要求。
4. **验证策略组合**：上游约 3–4 万级 lit/unittest 因 runtime 版本错配、无 runtimes 工程、musl/glibc、10800s 墙钟等具体技术原因无法整套启用；以 test_package 真实编译链接运行（3/3）作为 R34 反空壳证明，并在 MANIFEST/notes 写明豁免技术原因。

推广价值：可推广到同仓库其它 llvm-project 真机原生工具链（llvm / flang / lld 等），以及“自编 Clang 驱动但依赖 SDK compiler-rt 才能完整链接”的配方（castxml、cling、enzyme 等相关链路）。对后续同等中等难度、万级用例规模的工具链库，路径 B 知识复用价值大。

## 知识库查重与新增价值

- 新增 draft：`knowledge/drafts/DRAFT-clang-ohos-native-llvm-toolchain.kv`
- 拟提升编号：E258（最终编号由知识库主编确认）
- 条目主题：OHOS 真机原生构建 clang/llvm 工具链需组合处理平台识别、SDK 运行时捆绑与签名
- 查重关键词：clang、llvm-project、config.guess、Platform/HarmonyOS.cmake、CMAKE_SYSTEM_NAME、tblgen、clang_rt.crtbegin、OHOS_SDK_LLVM_ROOT、LLVM_BUILD_LLVM_DYLIB、binary-sign-tool、LLVM_INCLUDE_TESTS、中等难度、lit 三四万
- 覆盖判断：已有 E007/E160（autotools config.guess）与一般 CMake 平台识别、签名/打包操作文档，**未完整覆盖**「LLVM 真机原生 + 不设 SYSTEM_NAME 保 tblgen + SDK clang_rt 动态捆绑 + dylib 瘦身 + XPM 签名 + 大规模 lit 技术豁免」这一组合方案；本条目增量在于将该组合写成可跨库复用的路径 B 知识。

## 证据材料

| 项目 | 内容 |
|------|------|
| 原始失败 | 典型失败链：`Unable to determine platform` / `config.guess`/`get_host_triple`；缺 `clang_rt.crtbegin`/`libclang_rt.builtins` 无法链接；未签名 ELF 在 OHOS 上 `Permission denied`；过大静态 clang 触碰制品仓体积上限。早期 CI 曾因 GitHub 源码下载超时失败（CI #13135） |
| 修复方案 | `archives/c/clang/22.1.8/conanfile.py` 组合实现：stub config.guess、注入 Platform/HarmonyOS.cmake、dylib、动态 SDK/`clang_rt` 发现、ConanException 硬失败、ELF 签名；知识草稿见上。关键提交：`e503884c` / `4281c117` / `439ada9f` / `e8b1e877` / `985b2b0c` / `db0a4fdf` / `dd820cd3` |
| 构建验证 | HarmonyOS PC aarch64 真机原生；conan create；G0–G4 PASS |
| 上游测试 | 上游 lit/unittest 约 **3–4 万**量级；未启用全量 check-clang/check-llvm（有技术豁免，见 test_package/MANIFEST.yml 与 notes.md 五条原因）；非“偷懒未测” |
| 消费者验证 | test_package 3/3 = 100%（clang --version + C 编译链接运行 + C++ 编译链接运行）；CI 曾实跑通过 #12672 / #13006（日志 id #13447 / #13839） |
| 审查证据 | AI review：P0（误删 open-mpi 超时）已修；硬编码 SDK/15.0.4 Medium 建议已按动态发现落实；test_package 无效 OHOS_SDK_LLVM_ROOT 显式失败已对齐 |
| 当前 CI | 以 PR 页最新为准；曾出现 checkout-pr 拉 3868.diff 瞬时失败（#13953，exit 60，非配方源码问题），后续提交已触发重跑 |

测试框架说明：本库为中等难度工具链配方；上游 lit/unittest 约 3–4 万级，因平台能力缺口整套豁免；替代验证为 test_package 全链路探针 + L2 smoke（116/117）等。

## 申请分值

- 路径 B 贡献创新：10 分候选
- 理由：clang 为中等难度、上游约 3–4 万级用例的工具链库，按路径 B 沉淀「真机原生构建 clang」组合适配知识（含禁止项：禁止设 SYSTEM_NAME、禁止硬编码 SDK/15.0.4、禁止静默跳过 runtime），跨库复用价值大；与导师「建议按路径 B、价值很大」的评审口径一致
- 测试框架/工具链验证作为路径 B 证明材料，不重复申报额外分值。最终以官方审核为准

## 其他说明

- 本 Issue 按路径 B 申报；不再按路径 A 基础适配分值单独申报（PR 描述已同步为路径 B）
- 未申报 Path C / 依赖库附加分 / HarmonyOS 系统差异新发现专项
- `ci/config/build_timeouts.txt` 含 `clang/22.1.8 10800`，并保留 `open-mpi/5.0.10 10800`
- `conandata.yml` 保持单值官方 GitHub URL（R39），镜像由 CI fallback

## 需要官方确认的问题

1. 是否认可本 PR 按路径 B（贡献创新，10 分候选）评审——尤其基于中等难度 + 约 3–4 万级上游用例的知识沉淀价值
2. 是否认可「OHOS 真机原生 llvm/clang 工具链组合适配」属于可跨库复用的适配知识
3. 是否认可修复 + 验证证据，并允许草稿在主编审核时确定最终编号（拟 E258）
