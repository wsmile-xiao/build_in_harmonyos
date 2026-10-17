# DRAFT-odin-llvm-constrained-toolchain-bootstrap：OHOS 受限 LLVM 工具链上的自举型语言编译器适配模式

> 状态：草稿（draft），不预占正式编号；最终编号由知识库主编确认。
> 触发事件：odin dev-2026-08 HarmonyOS PC 适配（PR #10021，CI #47478 绿）。
> 证据权威：`learninglog/20260912odin-dev-2026-08/证据七环.md`（七环 + 12 轮编译史）。
> 跨库旁证：`learninglog/20260912odinfmt-dev-2026-06/失败路径.md`、`learninglog/20260912ols-dev-2026-06/失败路径.md`。

## 现象

以 LLVM 为后端的语言编译器在 OHOS 上会连续撞到四个独立门禁，报错原文如下。

> 术语澄清（避免误读）：Odin 编译器本体是 C++（`src/main.cpp` unity build 14 个 cpp + `src/libtommath.cpp`），**不是**用 Odin 写的自举编译器。本文的"自举型"指**自举闭环**性质：交付的工具链必须能用自己的产物再编译并运行本语言程序（Odin 的 `test_package` 第 3 项即此闭环），而 odinfmt / ols 这类下游工具更进一步——它们的源码本身就是 Odin 写的，必须先有可用的 odin 才能构建。两者共用同一套"受限 LLVM 工具链"诊断模式。

1. **LLVM 版本门禁**（`build_odin.sh`，只接受 LLVM 17-22；宿主 `llvm-config` 15.0.4）：

```text
ERROR: No supported llvm-config command found. Set LLVM_CONFIG to proceed. We suggest LLVM 22.
ERROR: Unsupported LLVM version 15.0.4: must be 17, 18, 19, 20, 21 or 22
```

（odinfmt / ols 任务的 `odin-bootstrap-llvm15.log` 记录同源报错。）

2. **聚合库符号缺失**（`src/llvm_backend.cpp` L3065-3111 按 arch 分支调用 per-target 初始化符号）：

```text
src/llvm_backend.cpp:3101:3: error: use of undeclared identifier 'LLVMInitializeARMTargetInfo'; did you mean 'LLVMInitializeAllTargetInfos'?
src/llvm_backend.cpp:3102:3: error: use of undeclared identifier 'LLVMInitializeARMTarget'; did you mean 'LLVMInitializeAllTargets'?
src/llvm_backend.cpp:3106:3: error: use of undeclared identifier 'LLVMInitializeARMDisassembler'; did you mean 'LLVMInitializeAllDisassemblers'?
```

3. **运行期动态库加载失败（最易误诊）**（冒烟 `odin version`）：

```text
Error loading shared library libLLVM.so.22.1: (needed by .../build-ohos/odin)
Error relocating .../build-ohos/odin: LLVMGetFirstFunction: symbol not found
Error relocating .../build-ohos/odin: LLVMGetNextFunction: symbol not found
...（300+ 条同族，rc=127）
```

4. **平台识别门禁**（`build_odin.sh` L104-L140 `case "$OS_NAME"` 无 HarmonyOS 分支，落 `*`）：

```text
ERROR: Platform "HarmonyOS" unsupported
```

（实测宿主 `uname -m` = aarch64、`uname -s` = HarmonyOS；目标即本机，属本地构建而非交叉编译。）

## 根因

这类语言编译器把宿主 LLVM 工具链当作隐含前提，构建脚本在三处硬编码了这种耦合，运行期还有一处独立的环境误诊：

- **版本门禁**：上游要求 LLVM 17-22，OHOS SDK 自带 LLVM 15.0.4，宿主无包管理器、harmonybrew 环境损坏也无法装 LLVM 17+ → 必须换用制品仓的 LLVM，而不是绕过上游下限。
- **聚合库符号**：制品仓 `llvm/22.1.0` 交付 AArch64-only 聚合库 `libLLVM.so.22.1`（SONAME，符号版本 `LLVM_22.1`），`llvm-c/Target.h` 只生成 All 系列与 AArch64 的 per-target 声明；源码按 arch 分支直接引用 per-target 符号 → 非 AArch64 分支在编译期即 undeclared。
- **平台识别**：脚本只认 Linux/Darwin/Windows 一类 `$OS_NAME`，HarmonyOS 落 `*` 直接拒绝。
- **运行期误诊**：冒烟用了 `env="conanbuild"`，该环境只注入 SDK LLVM 15 的路径，`LD_LIBRARY_PATH` 未指向 `llvm/22.1.0/lib`，于是加载失败并连带整批 `Error relocating ... symbol not found`。症状看起来像"新版 LLVM ABI 不兼容"，实际与 ABI 无关——**odinfmt/ols 的"新版 LLVM 动态库加载即 bad_cast → 自举不可行"结论正是据此误诊得出的，本条目予以推翻**：改用 `conanrun` 后同一批库可正常加载运行。

此外源码获取链路本身也不通：`codeload.github.com:443` 超时、gitcode 镜像 tree 无 `tools/`（`git ls-tree HEAD` 无 tools/ 目录）。

## 可复用修复模式（五要点）

适用于任何"以 LLVM 为后端的语言编译器 + 受限 LLVM 工具链"的组合（含需要自举闭环验证的工具链，以及用该语言自写的下游工具），五个子模式可独立命中也可叠加：

1. **版本门禁 → 用制品仓 LLVM 替代宿主工具链**
   宿主 `llvm-config` 版本不在上游白名单时，不要放宽上游下限，而是把 `llvm/22.1.0` 作为 `tool_requires`，并把 `LLVM_CONFIG` 指向该包的 `llvm-config`。
   判据：`llvm-config --version` 落进上游白名单区间（17-22）即可通过门禁。

2. **聚合库符号 → per-target `LLVMInitialize*` 必须改 `All` 系列**
   对 AArch64-only 聚合库，把 `src/llvm_backend.cpp` 架构 switch 中所有 `LLVMInitialize<Arch>TargetInfo/Target/TargetMC/AsmPrinter/AsmParser/Disassembler` 统一改为 `LLVMInitializeAllTargetInfos/Targets/TargetMCs/AsmPrinters/AsmParsers/Disassemblers`。
   本条补丁：`patches/0001-llvm-backend-all-target-init.patch`，sha256 `c30f86e31791248b8a35ec70724c2c7942aa95a325a903138104e1cb4978bcf8`。
   注意：**漏掉任一架构分支会立刻复发**（历史上 `TargetArch_arm32` 分支漏改，r8 轮即报同族 undeclared）。

3. **运行期环境 → `conanrun` 而不是 `conanbuild`（本条目最大增量）**
   需要 LLVM 共享库的冒烟/test 调用一律用 `self.run(..., env="conanrun")`。`conanbuild` 只注入 SDK LLVM 15 路径，症状是加载失败 + 大批符号重定位失败，会被误读成 ABI 问题。
   区分手段（务必执行）：跑只链接 `libLLVM.so.<major>` 的最小动态链接探针。探针在错误 `LD_LIBRARY_PATH` 下失败、在 `conanrun` 下 rc=0，即证明是环境注入问题；只有探针在正确路径下仍 `rc=134 bad_cast`，才可判 ABI 不兼容。

4. **平台识别 → `uname` 映射为 Linux**
   `build_odin.sh` 的 `case "$OS_NAME"` 增加 HarmonyOS → Linux 映射（保留 aarch64 目标语义）。属构建脚本层的平台别名，不是交叉编译。

5. **源码获取 → 离线源 + 双源 sha256 核对**
   直连 github 不可达、镜像缺 `tools/` 时，用本地 tarball 经 `file://` 离线源构建，sha256 与 `conandata.yml` 双源核对一致；**提交前必须还原为官方 URL**，避免把离线路径写进交付面。

## 验证证据

| 项目 | 内容 |
| --- | --- |
| 构建 rc | `conan create` **rc=0**（r12，CI 等价命令 `-pr:h= -pr:b= --build=odin/*` 强制全量重建：编译 → 签名 → 冒烟 → 打包 → test_package）；r11 复用 r10 已建包仅重跑 test_package 亦 rc=0；编译 22 warnings / 0 error |
| 编译轮次 | r1~r12 完整失败史见 `证据七环.md`「编译轮次记录」；决定性两轮：r8（per-target undeclared，patch 漏 arm32 分支）、r9（`conanbuild` 误注入 → 300+ relocating 失败） |
| test_package | **3/3 通过**：①`odin version` → `odin version dev-2026-08`；②`hello.odin` → `Hello from Odin on HarmonyOS!`；③`math_probe.odin`（自举：`odin build` 自编译并运行）→ `sqrt(144) = 12`，assert 通过 |
| 上游测试 | **0/501（未运行，如实记录）**：上游 `tests/` 209 个 `.odin`（501 个 `@(test)` 过程）需 `download_assets.py` 联网拉取测试资产并要求全组件多 LLVM 后端，本包为 AArch64 聚合库不满足；不伪造通过率 |
| CI | PR #10021：第 1 轮 #47470（Worker OpenHarmonyPCDeveloper-CI-037）红于 Worker 侧 `git-clone`（`Error loading shared library libz.so: (needed by /data/service/hnp/bin/git)`，未进入代码构建）；第 2 轮 **#47478（Worker CI-026）绿**，`conan-build-test` 与 L0/L1 门禁全步骤 ✅，cleanup 日志含 `odin/dev-2026-08#eeda35ab…: Removed binaries: [...]` 即 CI 上完整建出 |
| CI 失败归因 | 第 1 轮红点为 Worker 状态问题：同期 #10019/#10016 同样红在 git-clone/libz，而 #10018/#10014/#10013/#10012/#10011/#10010/#10008/#10007 在 CI-021/026/032/007 上为绿；换 Worker 后即绿，非本 PR 代码问题 |
| AI review | 2026-09-15 00:34 触发，结论「#### 代码审查 / ✅ 未发现问题」（无 P0/P1） |

## 关系与边界

- `similar_to`：E349（vlang 自举编译器的 bootstrap 源固定与阶段产物签名）、E356（固定目标编译器不混 ABI 的验证）、E486（引导构建期宿主 ELF 首次执行前签名）、E218 / E286（OHOS SDK LLVM 共享库的链接与组件缺口）。
- 本条**不覆盖**上述条目，上述条目也**不覆盖**本条：它们处理的是"自举流程的产物签名/测试验证/工具名替换/SDK LLVM 组件缺失"，本条处理的是"**宿主 LLVM 版本不在上游门禁内 + 聚合库 per-target 符号缺失 + 运行期库路径注入环境选错**"这一组合，且包含一条对既有结论的实质性修正（bad_cast 误诊）。
- 推广价值：odinfmt / ols（同批任务的阻塞结论可直接解除）、其他以内嵌 LLVM 为后端的自举语言工具链，以及任何直接引用 per-target `LLVMInitialize*` 或依赖 `conanbuild`/`conanrun` 区分注入 LLVM 运行时的配方。
