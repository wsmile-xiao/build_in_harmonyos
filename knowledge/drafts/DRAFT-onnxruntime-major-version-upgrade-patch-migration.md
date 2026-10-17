# DRAFT-onnxruntime-major-version-upgrade-patch-migration：大库版本升级在 OHOS 交叉链上的三类故障组合

> 触发事件：onnxruntime 1.27.1 → 1.28.0 版本升级（`archives/o/onnxruntime/1.28.0`，PR #9776）
> 证据源：本任务证据七环（`learninglog/20260912onnxruntime-1.28.0/证据七环.md`）

## 现象

一个带补丁集的大型 C/C++ 库升一个 minor 版本，会在同一条链上先后打出三类完全不同的报错。
它们不是并列的三件事，而是**串联**的：前一个不修掉，后一个根本不暴露。

### 一、补丁 hunk 跨版本失配（事件 2/3）

上游 1.28.0 重构了被补丁命中的文件结构（`cmake/onnxruntime_mlas.cmake` 把 `set_source_files_properties` 块改为
`list(APPEND mlas_platform_srcs)` 并统一设置），旧补丁的上下文对不上了：

```text
patches/0002-cmake-onnxruntime_mlas.cmake.patch: hunk no.1 doesn't match source file at line 598
expected: set_source_files_properties(${MLAS_SRC_DIR}/halfgemm_kernel_neon_fp16.cpp ...)
actual  : ${MLAS_SRC_DIR}/eltwise_kernel_neon_fp16.cpp
```

同批次的 `0003`/`0005` 也因上游把补丁目录改为 `vcpkg-ports/abseil/`、删除 duktape 块、新增 dawn 行而偏移，
`git apply --check` FAIL（`abseil-cpp.cmake:11` / `:743`）。

这里的陷阱是：**`git apply --check` 会靠 fuzz 容错放行，而 Conan 的 Python patch 库要求精确上下文**。
于是本机校验通过、`conan create` 才报错。

### 二、宿主工具构建未继承 conan profile `[buildenv]`（事件 6）

补丁修好后，CI 首轮（构建 #45543 / Worker `OpenHarmonyPCDeveloper-CI-021`）报出了完全另一类错误：

```text
Error loading shared library libxml2.so.16: (needed by .../ohos/native/llvm/bin/lld)
Error relocating .../lld: xmlFreeDoc: symbol not found
clang-15: error: unable to execute command: No such file or directory
clang-15: error: linker command failed due to signal (use -v to see invocation)
...
ERROR: onnxruntime/1.28.0: Error in build() method, line 66
    protoc_path = self._build_protoc()
while calling '_build_protoc', line 250
    subprocess.run([...])
    CalledProcessError: ... returned non-zero exit status 1
```

配方 `conanfile.py:250` 用**裸 `subprocess.run()`** 构建宿主工具 protoc。裸进程不继承 profile 的 `[buildenv]`，
CI worker 没有环境 `LD_LIBRARY_PATH`，OHOS SDK 的 `lld`（已 strip、无 RUNPATH）找不到同目录 `llvm/lib` 下的
`libxml2.so.16`，链接器起不来 → protoc 构建不出来 → 全量构建中断。
本地之所以一直是绿的，是因为 agent shell 里恰好已有 `LD_LIBRARY_PATH`，把缺陷掩盖了。

### 三、失效镜像链耗尽 CI 构建预算（事件 5/7）

修完环境继承后，CI 第二轮（构建 #47526 / Worker `OpenHarmonyPCDeveloper-CI-032`）报超时：

```text
onnxruntime/1.28.0: WARN:   download failed from https://gh-proxy.com/...: 403: Forbidden
onnxruntime/1.28.0: WARN: network: Error downloading file https://mirror.ghproxy.com/...: ConnectTimeoutError(... connect timeout=30 ...)
onnxruntime/1.28.0: WARN: network: Error downloading file https://ghproxy.com/...: ReadTimeoutError(... read timeout=30 ...)
onnxruntime/1.28.0: WARN: network: Error downloading file https://gitclone.com/...: ResponseError('too many 500/502 error responses')
onnxruntime/1.28.0: WARN:   download failed from https://moeyy.cn/gh-proxy/...: Not found
onnxruntime/1.28.0: WARN: network: Error downloading file https://kkgithub.com/...: CERTIFICATE_VERIFY_FAILED certificate has expired
onnxruntime/1.28.0: WARN: network: Error downloading file https://github.com/...  ← 最后才试官方源
[fail] onnxruntime/1.28.0 — conan create TIMED OUT after 3600s
  Failed packages: onnxruntime/1.28.0 (timeout)
elapsedTime=3609.031280
```

更早一轮（r3）还暴露了这条回退路径本身是坏的 —— `ConanOutput.warn()` 在 Conan 2.x 已移除：

```text
ERROR: onnxruntime/1.28.0: Error in build() method, line 63
    self._download_deps()
while calling '_download_with_mirrors', line 167
    self.output.warn(f"  download failed from {mirror_url}: {e}")
    AttributeError: 'ConanOutput' object has no attribute 'warn'
```

即首个镜像一失败就抛异常，根本走不到后续镜像与官方源（全文件 5 处同源写法）。

**背景引述（不作主模式）**：本次升级还遇到 ONNX 1.22.0 `tensor.h:54/61` 在 `-fno-exceptions` 下原生
`throw` 报 `cannot use 'throw' with exceptions disabled`（onnx 特定源码问题）；以及第 2 轮编译到 82%
时 `op_kernel.h: Operation not permitted`（宿主内存紧张 + HMFS 半写文件的环境事故）。

## 根因

三者的共同结构是：**本机环境与 CI 干净环境的语义差异，被「前一层的成功」掩盖**。

1. **补丁迁移**：`git apply --check` 带 fuzz 容错、Conan patch 库要求精确上下文，两个校验器语义不同。
   手工调 hunk 偏移只是让本机通过，目标版本源码一升级就再次失配。
2. **环境泄漏**：`subprocess.run()` 是裸进程调用，不经过 Conan 的 profile `[buildenv]` 环境合成。
   配方内任何宿主工具构建都不能假设 agent shell 里的变量存在 —— 这是「本地绿 CI 红」的典型成因。
3. **镜像预算**：把 6 个第三方代理排在官方源之前。镜像全失效时，每个候选都要耗满
   connect/read 超时与重试预算（单依赖约 10 分钟），12 个 FetchContent 依赖累计超出
   `conan create` 的 3600s 上限，表现为 `TIMED OUT` 且从未进入编译阶段（`L0_RESULT=pass`）。
   而日志显示官方 `github.com` 在 CI worker 上**实测可达**（278MB 源码 tarball 与全部依赖最终都由它提供）。

## 可复用修复模式

### 诊断顺序：补丁 → 环境 → 网络预算

```
升级后 conan create 失败
├─ 报 hunk doesn't match / patch failed
│   └─ ① 补丁集跨版本迁移：不要调 hunk，按目标版本源码重新生成全部补丁
│        黄金验证 = 干净树应用后与 .work 树 diff=0
├─ 补丁问题修掉后转成链接器/宿主工具报错（lld、libxml2.so、symbol not found）
│   └─ ② 宿主工具 buildenv 继承：subprocess.run → self.run(..., env="conanbuild")
│        判据 = 本地绿 CI 红，先查环境继承而非源码
└─ 再修掉后转成下载超时/TIMED OUT（门禁全过、没进编译）
    └─ ③ 镜像排序：官方源实测可达就排首位；镜像仅回退；每候选单次尝试（retry=1）
```

### ① 补丁集精确迁移

- **不要**手工调 hunk 偏移，也**不要**依赖 fuzz 容错通过校验；
- 直接从 `.orig`/`.work` 树 `diff` 重新生成全部补丁，上下文由目标版本源码自动产出；
- 黄金验证：干净树应用后与原工作树 `diff=0`；
- 只改源文件、不碰生成文件（否则补丁不可向上游提交，P005/P011）。

### ② 宿主工具 buildenv 继承

- 配方内一切宿主工具构建改用 conan 的 `self.run(..., env="conanbuild")`，由 conan 按
  profile `[buildenv]` 合成工具链环境；
- 禁止在配方里手工 `export`/写死 agent shell 的 `LD_LIBRARY_PATH`（那是把本地污染固化进配方）；
- 经验判据：**「本地绿、CI 红的宿主工具构建」，先查环境继承，再查源码**。

### ③ 镜像排序与预算

- 官方源实测可达时直连优先，镜像降级为回退；
- 每个候选把重试压到单次（`retry=1` = 2 次尝试，足够吸收单次瞬断），避免把 CI 构建预算
  消耗在死镜像的重试上；
- 顺手修 `self.output.warn` → `self.output.warning`（Conan 2.x 已移除 `warn`），否则首个镜像
  失败就抛 `AttributeError` 中断，回退链形同不存在。

## 验证证据

- **本地全量构建**：`conan create` rc=0 三轮 —— r1（补丁重新生成后首次全量编译成功）、
  r6（修复后全量编译 + 打包 + test_package 构建链接全通过，约 34 分钟）、
  r7（官方源优先改动后复验：移开预置 mirror，12 个依赖全部由官方源真实下载，全量编译通过，约 42 分钟）。
- **产物一致性**：`libonnxruntime.so.1.28.0`（ELF 64-bit LSB arm64, stripped, 9,013,120 字节）
  + `.so.1`/`.so` 软链 + 17 个 `.h`（含 `core/` 子目录）+ 1 个 `.inc` + `libonnxruntime.pc`
  + 4 个 cmake config，形态与 1.27.1 对齐。
- **上游测试计数**：onnxruntime 上游 gtest 用例 8444（595 个测试源文件，`onnxruntime/test/` 宏计数）；
  本次为 minimal build（`onnxruntime_BUILD_UNIT_TESTS=OFF`，与 1.27.1 一致），执行 0/8444；
  ONNX 模型一致性测试需完整构建 + 模型库，未启用。
- **test_package**：1/1 —— `test_onnxruntime.cpp`（`OrtGetApiBase()` 版本号冒烟）CMake configure ✅、
  编译 ✅、链接 ✅（`[100%] Built target test_onnxruntime`），rc=0；`test()` 实际运行
  `can_run()=False`（交叉编译产物不可在构建机执行），与 1.27.1 行为一致，运行验证由 CI 设备侧执行。
- **CI 轮次**：`#45543`（Worker CI-021，事件 6 根因）→ `#47526`（Worker CI-032，事件 7 镜像超时）
  → 修复 commit `fc787ba38a`（`_build_protoc()` 改 `self.run(..., env="conanbuild")`；
  5 处 `output.warn` → `output.warning`）→ `#47919`（Worker CI-026）。
- **AI 检视**：第 1 轮（commit `fc787ba38a`）atomgit-bot comment `189675581`
  「#### 代码审查 ✅ 未发现问题」，无 P0/P1，无检视意见需闭环。
- **可独立复现的判据**：① 补丁干净树应用后 `diff=0`；② `grep 'env="conanbuild"' conanfile.py` 命中；
  ③ CI 日志中官方源 `github.com` 先于镜像出现。

## 关系与相邻条目

- `similar_to`：E132（OHOS SDK lld 缺 libxml2.so.16 → 设 LD_LIBRARY_PATH）、
  E227（补丁用 git / GNU patch 双解析器零 fuzz 校验）、
  E299（Conan 源码获取失败分层诊断）、E372（官方源优先 + 权威镜像回退）、
  E526（`apply_conandata_patches` strip=0 语义）、E282（多源码 `base_path` 路由）。
- 上述条目均为**单点**覆盖：或只谈补丁校验、或只谈链接器环境变量、或只谈下载分层；
  本条目增量是**三者的组合与互相咬合的诊断树**，以及两个此前无覆盖的机制层结论 ——
  「跨版本升级时补丁集如何重生成」与「Conan 配方内宿主工具如何继承 buildenv」。
