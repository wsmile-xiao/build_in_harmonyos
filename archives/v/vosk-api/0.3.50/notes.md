# vosk-api 0.3.50 适配笔记（OHOS aarch64 / 设备原生）

## 基本信息

- 任务声明语言：cpp（本 SKILL conan 流程 c/cpp 通吃）
- 上游仓库：https://github.com/alphacep/vosk-api
- 上游 tag：`v0.3.50`（GitHub archive tarball）
- 源码 tarball：`https://github.com/alphacep/vosk-api/archive/refs/tags/v0.3.50.tar.gz`
- SHA-256：`cc1067bcc599c9a2f5f38d4257caf2ac636ba244f7c965cee20293a41024f70f`（tarball 实测，`sha256sum`）
- 许可证：Apache-2.0（COPYING）
- 构建系统：CMake（顶层 `CMakeLists.txt`，`project(vosk-api CXX)`，`cmake_minimum_required(VERSION 3.13)`）
- 分支：`feat/vosk-api-0.3.50`
- 设备：HarmonyOS PC（`uname -srm` = `HarmonyOS HongMeng Kernel 1.12.0 aarch64`），clang 15.0.4，cmake 4.1.2，make 4.4.1，conan 2.29.1（OHOS 适配版）

## 交付面定位（语言核验）

本包只构建 **C API 核心库 `libvosk.so` + `vosk_api.h`**（上游 `src/*.cc`）。
仓库内的 `python/`、`java/`、`kotlin/`、`csharp/`、`nodejs/`、`rust/`、`go/`、
`webjs/` 只提供各语言的**绑定**，它们都是 libvosk.so 的消费者，不参与本包构建。

## 语言预检偏差记录（R47）

`ohc-run.py lang-preflight vosk-api 0.3.50 --src $BUILD_SRC_DIR` 判定 `env_unsupported`
（detected=python），人工复核为**误判**：

- 工具取数：`源文件 61 个（python:23, bash:23, java:16, nodejs:8），主体占比 38%`，
  manifest 判据命中仓库内 `python/setup.py`。
- 证据 1（构建系统）：顶层 `CMakeLists.txt` 为 `project(vosk-api CXX)`，C++ 项目；
  与之并列的 `python/setup.py` 只是 **子目录** 里的 Python 绑定打包清单
  （`packages=setuptools.find_packages()` + `package_data={'vosk': ['*.so']}`），
  并非仓库级 manifest —— 工具对 `setup.py/Cargo.toml` 类判据使用全树文件名集合，
  会把子目录绑定清单误当仓库 manifest。
- 证据 2（主体）：真正被构建的编译单元是 `src/{language_model,model,recognizer,
  spk_model,vosk_api,postprocessor}.cc`（C++17），产物是 `libvosk.so`。
  工具自身的边界规则 D.4-2 明文规定"绑定类包按 C++ 主体判 cpp"，本仓库正是
  "C++ 库 + 多语言绑定"形态，只是绑定不是 pybind11，故未触发该分支。
- 结论：任务声明 `cpp` 正确，按 C++ 适配继续；本偏差按 bool/bshoshany-thread-pool
  等既有"辅助/绑定语言误报"经验处理，不改动上游文件。

## W0 依赖预检（R36）

`conan download <ref> -r=ohpcd --only-recipe` 逐个实测：

| 依赖 | 制品仓状态 | 说明 |
|------|-----------|------|
| `kaldi/g20231112` | ✅ 已发布（含 binary） | 静态库 `libkaldi-*.a`（21 个）+ headers |
| `openfst/1.8.4` | ✅ 已发布 | FST 核心（`libfst.a`/`libfstscript.a`） |
| `libfstngram/1.8.4` | ✅ 已发布 | OpenFst NGramFst(LOUDS) 扩展，vosk 硬依赖 |
| `openblas/0.3.34` | ✅ 已发布 | kaldi 的 BLAS/LAPACK 后端（shared-library） |

依赖链拓扑：`vosk-api → kaldi → (openfst, openblas)`，`vosk-api → (openfst, libfstngram)`。
所有依赖均已发布，无 R36 阻塞。

> 关键点：`openfst/1.8.4` 上游默认 `--enable-ngram-fsts=no`，**不产出** ngram 扩展
> （实测包内无 `include/fst/extensions/`、无 `libfstngram.a`），而 `src/model.cc`
> 直接 `#include <fst/extensions/ngram/ngram-fst.h>` 并注册
> `FstRegisterer<NGramFst<StdArc>>`。本仓已把该扩展独立打包为 `libfstngram/1.8.4`，
> 故必须显式依赖它，否则编译期即缺头文件。

## 编译步骤（真实命令）

```bash
# 1. 初始化
python3 scripts/ohc-run.py init-build vosk-api 0.3.50 \
  --url=https://github.com/alphacep/vosk-api/archive/refs/tags/v0.3.50.tar.gz

# 2. 语言预检（见上方偏差记录）
python3 scripts/ohc-run.py lang-preflight vosk-api 0.3.50 --src "$BUILD_SRC_DIR"

# 3. 探索期直接改源码（R3），再以 refresh-patch --auto 生成补丁
#    改动：CMakeLists.txt（补 postprocessor.cc + Conan 目标）、
#          src/recognizer.cc（WordAlignLatticePartial -> WordAlignLattice）
python3 scripts/ohc-run.py refresh-patch --auto vosk-api 0.3.50

# 4. 配方验证（G0-G4 + L2/L4/L5 八道门禁）
python3 scripts/ohc-run.py conan-verify vosk-api 0.3.50

# 5. 收尾（内含 W2 结构检查 + R36 依赖检查 + W3 conan create）
python3 scripts/ohc-run.py finish vosk-api 0.3.50 built
```

配方的实际构建命令（由 recipe 生成，等价手工复核）：

```bash
conan create archives/v/vosk-api/0.3.50 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
#   generate: CMakeDeps + CMakeToolchain(BUILD_SHARED_LIBS=ON)
#   build:    apply_conandata_patches -> cmake.configure -> cmake.build
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `init-build` 复制源码失败：`Operation not permitted`（os.link）→ 回退 copy2 又因 `training/steps`、`training/utils` 两个悬空符号链接报错 | HMDFS 不支持硬链接（E011 族）；上游 tarball 里 `training/{steps,utils}` 是指向 Kaldi 训练脚本的悬空 symlink | 手工用 tar 管道完成 `.work` 复制（248 文件与 `.orig` 对齐，仅缺那 2 个与应用无关的悬空链接），再重跑 `init-build`（orig/work 均已就绪即跳过复制） |
| 2 | `recognizer.cc:847: error: use of undeclared identifier 'WordAlignLatticePartial'` | vosk 0.3.50 面向 alphacep/kaldi 分支；kaldi-asr/kaldi 自 g20231112 起已把 `WordAlignLatticePartial` 合并进 `kaldi::WordAlignLattice`（签名一致，语义为 partial-word 感知的词对齐） | `patches/0002`：改用 `WordAlignLattice` |
| 3 | 链接失败（未走到）：上游 CMakeLists 的 sources 列表漏写 `src/postprocessor.cc`，而 `vosk_api.cc` 的 `vosk_text_processor_new/itn` 引用其 `Processor` 符号 | 上游 `src/Makefile` 的 `VOSK_SOURCES` 含 postprocessor.cc，CMake 路径漏同步（上游 CMake 路径实际未被其 CI 使用，只构建 wheel） | `patches/0001`：补入 `src/postprocessor.cc` |
| 4 | `find_package(kaldi REQUIRED)` 后 `target_link_libraries(... kaldi-base kaldi-online2 kaldi-rnnlm fstngram)` 无法用 Conan 包满足 | 该写法假设发行版安装态 kaldi 导出的 cmake 目标与 openfst 安装态裸库名 `fstngram` | `patches/0001`：改为 `find_package(libfstngram REQUIRED)` + `target_link_libraries(vosk PUBLIC kaldi::kaldi libfstngram::libfstngram)` |
| 5 | `make: jobserver mkfifo: ... Operation not permitted` 告警 | OHOS/HMDFS 上 make jobserver FIFO 创建受限 | 配方 `generate()` 设 `CMAKE_BUILD_PARALLEL_LEVEL=1`（串行构建，避免 jobserver 与内存超订） |
| 6 | cmake 4.1 输出 `System is unknown to cmake, create Platform/HarmonyOS` | cmake 无内置 HarmonyOS 平台文件；Conan 的 CMakeToolchain 已把 OHOS 映射为 `CMAKE_SYSTEM_NAME=HarmonyOS` | 无需处理（GNUInstallDirs 仍正确给出 `lib/`、`include/`），仅一条 notice |
| 7 | W3/CI `L5a: libvosk.so 缺少 DT_SONAME`（soname_gate_failed） | 上游 CMakeLists 既未设 `VERSION` 也未设 `SOVERSION`，链接器不产出 `DT_SONAME`；下游按完整路径链接会把构建机绝对路径写进 `DT_NEEDED` | `patches/0001`：`target_link_options(vosk PRIVATE "-Wl,-soname,libvosk.so")`，产物 `readelf -d` 实测 `SONAME: [libvosk.so]`（相对路径） |

## 源码修改（patches/）

1. `0001-CMakeLists.txt.patch`（+12/-1）
   - `add_library(vosk ...)` 补入 `src/postprocessor.cc`；
   - 链接目标改为 `kaldi::kaldi` + `libfstngram::libfstngram`（Conan/CMakeDeps 目标），
     并补 `find_package(libfstngram REQUIRED)`；
   - 补 `-Wl,-soname,libvosk.so`（上游未设 VERSION/SOVERSION，无 DT_SONAME，
     W3/CI 的 L5a 质量门禁会拦截）。
2. `0002-src-recognizer.cc.patch`（+1/-1）
   - `WordAlignLatticePartial(...)` → `WordAlignLattice(...)`（kaldi g20231112 API 合并）。

两个补丁均不含平台宏（无 `__OHOS__`），不涉及 stub/降级实现，属构建系统与依赖 API 迁移。

## 依赖版本

- `kaldi/g20231112`（静态库）
- `openfst/1.8.4`（静态库）
- `libfstngram/1.8.4`（静态库，OpenFst NGramFst 扩展）
- `openblas/0.3.34`（shared-library，kaldi 的 BLAS/LAPACK 后端，Conan 传递）

## 上游测试账本（R51）

**清点结论：上游没有自动化测试套件，自动化用例数 N = 0。**

证据（源码树与 CI 配置静态清点）：

| 检查项 | 实测 | 结论 |
|--------|------|------|
| `tests/` 目录 | 不存在（源码树顶层 17 个目录，无 tests/） | 无测试目录 |
| `enable_testing()` / `add_test()` | 顶层 `CMakeLists.txt` 全文 20 行，均未出现 | 无 CTest 注册 |
| pytest / gtest / doctest 注册 | 全树 grep 无 | 无单测框架 |
| `.travis.yml` | 4 个 job 只有 `travis/build-wheels.sh`（构建 Python wheel） | CI 不跑测试 |
| `python/test/transcribe_scp.py` | 转写辅助脚本（读 scp 列表） | 非测试套件 |
| `python/example/*.py` | 18 个面向用户的示例脚本 | 非测试套件 |

**上游真实测试入口（人工验证程序，非自动化）**：

| 入口 | 命令 | 阻塞原因 |
|------|------|----------|
| `c/Makefile` → `test_vosk` | `cd c && make && ./test_vosk` | `c/test_vosk.c:9` 打开写死的相对目录 `model`、`:15` 打开 `test.wav`，需要外部下载 Vosk 模型（alphacephei.com，本环境下载 40MB 模型实测被限速，未完成）；程序只 `printf` 结果，无断言/退出码约定 |
| `c/Makefile` → `test_vosk_speaker` | `cd c && make && ./test_vosk_speaker` | 同上，另需 speaker 模型 |

入口实测（本适配环境，日志 `reports/upstream-test-entry.log`）：按上游 `c/Makefile`
的编译方式把 `c/test_vosk.c` 链接到本包产出的 `libvosk.so`——编译 rc=0、运行 rc=139。
库正常加载，`vosk_model_new` 对缺失的 `model` 目录按契约返回 NULL 并打印
`ERROR (VoskAPI:Model():src/model.cc:132) Folder 'model' does not contain model files.`；
该示例程序自身不检查 NULL 返回值，随后继续使用该句柄而以 SIGSEGV 退出（128+11）——
属上游示例的写法限制，非适配缺陷（本仓 `test_package/test_vosk.c` 对同一契约做了显式断言）。
本次环境下载 Vosk 模型被限速未完成，故无识别文本层面的上游实测结果。

## 适配后新增测试

`test_package/`（消费者测试 + 鸿蒙专项测试，断言 17 条）：

- `test_vosk.c`（10 条断言）：以 **C** 语言链接 `vosk::vosk`——C API 可链接可调用；
  缺失模型目录时 `vosk_model_new`/`vosk_spk_model_new`/`vosk_batch_model_new`
  按契约返回 NULL（不 abort）；NULL 句柄释放为 no-op；
  `vosk_text_processor_new` 经 OpenFst `Fst::Read` 加载两个 identity 转移器后，
  `vosk_text_processor_itn` 做 `StringCompiler + Compose + ShortestPath` 往返，
  输出必须与输入逐字一致（3 组输入）——**模型无关的真实功能路径**。
- `make_identity_fst.cpp`：仅链 OpenFst 的夹具生成器（与 libvosk.so 分进程，
  避免两份静态 OpenFst 在同一地址空间）。
- `ohos_dlopen_probe.c` + `ohos_specific_test.sh`（7 条断言）：libvosk.so 为
  ELF64/AArch64；NEEDED 闭合（`libc++_shared.so`/`libc.so`/`libopenblas.so.0`，
  且无构建机绝对路径）；OHOS musl 加载器下 `dlopen` 成功且 10 个公开 C API
  符号可 `dlsym` 解析（复现 ctypes/Java/C# 绑定的消费路径）。

## 验证结果

```bash
# conan create（含 test_package）
conan create archives/v/vosk-api/0.3.50 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
#   test_package/test_vosk:        checks=10 failures=0
#   test_package/ohos_specific:    summary pass=7 fail=0
```

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libvosk.so` | C API 共享库（AArch64 ELF64，NEEDED: libopenblas.so.0 / libc++_shared.so / libc.so） |
| `include/vosk_api.h` | C API 头文件 |
| `licenses/COPYING` | Apache-2.0 许可证 |

无 `commands.json`：产物只有库文件，没有命令行工具（R38 不适用）。

## 注意事项

- libvosk.so 运行期需要 `libopenblas.so.0`（Conan 包 `openblas/0.3.34`）。
  消费者用 `conan install` 的 runenv（或把 openblas 的 `lib/` 加入
  `LD_LIBRARY_PATH`）即可解析；kaldi/openfst/libfstngram 已静态链入，
  不产生额外运行期依赖。
- 本地没有可下载的 Vosk 模型时，`vosk_model_new` 会返回 NULL 并打印
  `Folder '<path>' does not contain model files` —— 这是库的既定契约，
  不是适配缺陷。
---

**编译结束**: 2026-09-28 20:15
**最终状态**: built
