# osqp 1.0.0 适配笔记

## 编译环境
- 构建系统: cmake（上游 `cmake_minimum_required(VERSION 3.18)`）
- 编译日期: 2026-09-08
- 编译器: clang 15.0.4 / clang++（native OHOS aarch64，`/data/service/hnp/bin/clang`）
- CMake 4.1.2，Ninja/Make 可用；Conan 2.29.1（OHOS 适配版）
- 目标平台: HarmonyOS PC aarch64（profile `ci/conan/profiles/ohos-aarch64`，`os=OHOS`）
- 状态: built（本地验证通过，未上传制品仓）

## W0b 历史经验核验（必读项）
本机存在上一次未完成的 osqp 1.0.0 草稿（`~/tttt/backup_libs/osqp/1.0.0/`，
其 result.json 停留在 `partial / w3_finish_started`，从未进仓，制品仓亦无 osqp：
`conan download osqp/1.0.0 -r=ohpcd --only-recipe` → exit 1）。核验结论：

| 历史结论 | 是否可迁移 | 本次处理 |
|---|---|---|
| 上游 v1.0.0 用 CMake FetchContent 在配置期 git clone QDLDL v0.1.8 | ✅ 属实（`algebra/_common/lin_sys/qdldl/qdldl.cmake:6-9`） | 采纳，但**改用零补丁方案**（见下） |
| 历史方案（工作区未进仓草稿）：自建 `BUILD_QDLDL` 开关 + `add_subdirectory(vendor/qdldl)` 并配一份补丁 | ⚠️ 可行但偏离上游 | **不沿用**。CMake 原生 `FETCHCONTENT_SOURCE_DIR_QDLDL` 即可让上游 FetchContent 直接消费本地官方源码，无需修改上游构建文件；少一个补丁=少一处上游漂移风险 |
| 历史方案：`src/CMakeLists.txt` 中断分支纳入 OHOS/HarmonyOS | ✅ 必要（本次独立复现了同一链接错误） | 沿用同思路，作为**唯一补丁** `0001-src-CMakeLists.txt.patch` |
| 历史命令均在设备原生工具链上执行 | ✅ 与 CI 环境同构（CI 用同一 profile + clang/cmake/ninja，无 Rust/OCaml 等缺失工具链） | 本次命令在 CI 侧逐字可执行（除 GitHub 瞬时超时由 CI pre-download 兜底） |

## 编译步骤
1. 官方源码核验（本机下载后 sha256 实测）：
   - osqp v1.0.0 `https://github.com/osqp/osqp/archive/refs/tags/v1.0.0.tar.gz`
     → `dd6a1c2e7e921485697d5e7cdeeb043c712526c395b3700601f51d472a7d8e48`
   - QDLDL v0.1.8 `https://github.com/osqp/qdldl/archive/refs/tags/v0.1.8.tar.gz`
     → `ecf113fd6ad8714f16289eb4d5f4d8b27842b6775b978c39def5913f983f6daa`
     （v1.0.0 release notes 明确 “Updated QDLDL to 0.1.8”，与 FetchContent 的 GIT_TAG 一致）
   - Catch2 v2.13.6 `https://github.com/catchorg/Catch2/archive/refs/tags/v2.13.6.tar.gz`
     → `48dfbb77b9193653e4e72df9633d2e0383b9b625a47060759668480fdf24fbd4`（仅测试套件需要）
2. 依赖发布检查（W0/R35，隔离 CONAN_HOME 排除本机缓存干扰）：
   ```bash
   conan download qdldl/0.1.8 -r=ohpcd --only-recipe      # exit 0
   conan download catch2/2.13.10-r0 -r=ohpcd --only-recipe # exit 0
   conan install --requires=qdldl/0.1.8 --build=never -r=ohpcd  # exit 0，二进制 4b977264 从远端 Download
   ```
3. 探索构建（`.work` 目录，官方源码 + 1 处中断适配）：
   ```bash
   cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
     -DFETCHCONTENT_SOURCE_DIR_QDLDL=/storage/Users/currentUser/tmp/osqp-deps/qdldl-0.1.8 \
     -DFETCHCONTENT_SOURCE_DIR_CATCH2=/storage/Users/currentUser/tmp/osqp-deps/Catch2-2.13.6 \
     -DOSQP_BUILD_UNITTESTS=ON -DOSQP_BUILD_DEMO_EXE=OFF
   cmake --build build -j2
   ```
   基线（未打补丁）构建 exit=2；打补丁后 exit=0，产物
   `build/out/{libosqp.so,libosqpstatic.a,lin_alg_tester,osqp_tester,osqp_tester_custom_memory}`
4. 上游测试：`ctest --test-dir build --output-on-failure` → 3/3 Passed；
   逐用例统计见「验证结果」与 `reports/test-report.md`
5. Staging 安装验证：`cmake --install build --prefix $TEST_PREFIX` →
   `include/osqp/*`、`include/qdldl/*`、`lib/{libosqp.so,libosqpstatic.a}`、
   `lib/cmake/osqp/*`、`share/osqp/codegen_files/**`（含上游一并安装的 qdldl 头，
   配方 package() 里裁掉，避免与已发布的 qdldl/0.1.8 重复提供）
6. `ohc-run.py conan-init osqp 1.0.0` 生成骨架 → 人工完善配方；
   `ohc-run.py refresh-patch --auto osqp 1.0.0` 生成补丁；
   `conan create`（静态 + 共享各一次）与 `ohc-run.py conan-verify` 全通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 基线构建 `ld.lld: error: undefined symbol: osqp_start_interrupt_listener / osqp_is_interrupted / osqp_end_interrupt_listener`（exit 2） | 上游 `CMakeLists.txt:27-33` 只识别 Linux/Darwin/Windows；OHOS 上 `CMAKE_SYSTEM_NAME=HarmonyOS` → `IS_LINUX=OFF`，`src/CMakeLists.txt:64` 的 `elseif(IS_MAC OR IS_LINUX)` 不成立，`interrupt_unix.c` 未编入 OSQPLIB，而 `OSQP_ENABLE_INTERRUPT` 默认 ON 且 `osqp_api.c` 无条件引用这三个符号 | 补丁 `patches/0001-src-CMakeLists.txt.patch`：该分支追加 `OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" OR CMAKE_SYSTEM_NAME STREQUAL "OHOS"`（HarmonyOS/OHOS 提供 POSIX signal 语义）。仓内同类先例：ableton-link、aws-c-io、arpon 的 CMake 平台分支补丁 |
| 2 | `conan create` 首跑在 `source()` 报 `ConnectTimeout github.com:443 ... (connect timeout=30)`（exit 1） | 该设备到 GitHub 的通道瞬时抖动（同一 URL 用 curl 立刻可下载；qdldl 适配笔记 #1 同现象）。`core.download:retry` 属 core.* 不允许在命令行 profile 注入 | 直接重试 `conan create`（第 2 次即通过）；CI 侧由 `build_and_test.sh` 的 pre-download（curl `--retry 3` + 镜像 + `file://` 重写）兜底，配方无需改动 |
| 3 | 探索构建/配方首跑报 `Manually specified source directory is missing: FETCHCONTENT_SOURCE_DIR_QDLDL --> .../_offline_deps/qdldl-0.1.8` | `conan.tools.files.get(..., strip_root=True)` 已剥掉 tarball 顶层 `qdldl-0.1.8/`，源码直接落在 `_offline_deps/` 下，拼出的子目录名不存在 | 落到显式目录 `_offline_deps/qdldl`（source() 与 generate() 共用 `QDLDL_OFFLINE_SUBDIR` 常量，杜绝两处路径不一致） |
| 4 | `ohc-run.py conan-verify` / `finish` 之后 `conandata.yml` 残留 `gh-proxy.com` 镜像 URL 列表，并留下 `conandata.yml.orig` / `.ghfast-bak` | E017 预防注入 + CI mirror fallback 改写后还原不彻底（v12.17 已知家族） | 手工还原为官方单 URL 并删除工具产生的 `.orig`/`.ghfast-bak` 备份（JC1 禁止此类残留混入；该备份在每轮 conan-verify 中会重现，故提交前须再清一次并复验 PF7）。还原后 `conan create` 用官方 URL 构建通过（exit 0），**PF7 源URL闸复验 PASS** |
| 5 | `preflight.check_branch_and_paths`（PF9）本机抛 `FileNotFoundError: 'git'` | 本机沙箱只允许 `git` 以 cwd 形式执行，拒绝 `git -C <绝对路径>` 形态子进程 | 按 PF9 同口径手工核验（路径段数 + 分支名），结论 PASS；已记入 SKILL 反馈（建议 preflight 用 `cwd=` 而非 `-C`） |
| 6 | 软件级 `archives/o/osqp/README.md` 被 PF9 判“变更路径缺版本目录层” | PF9 要求 archives 变更路径 ≥5 段，而软件级 README.md 只有 4 段（ARCHIVE-SPEC 要求软件级 README，与 create-pr 硬闸冲突；近期合并样本多数不含软件级 README） | 本 PR 不携带软件级 README（内容已存至工作区 `osqp-1.0.0-adapt/pr-software-readme.md`，可入 PR 描述），冲突已作为 SKILL 反馈上报 |
| 7 | `strings libosqpstatic.a` 含构建目录绝对路径 | 仅来自 `__FILE__` 调试字符串（`src/codegen.c`），非硬编码资源路径；codegen 资源实际按 `CMAKE_INSTALL_DATAROOTDIR/osqp/codegen_files` 安装（`CMakeLists.txt:565-568`） | 无需处理，已确认可重定位 |

## 源码修改（全部为 osqp 自身文件；补丁由 refresh-patch --auto 生成）
- `src/CMakeLists.txt` — 中断监听实现的平台分支纳入 HarmonyOS/OHOS（唯一改动，+2/-1）
- 配方里用 `-DFETCHCONTENT_SOURCE_DIR_QDLDL` 覆盖上游 FetchContent 源目录：
  **不改上游任何文件**，因此不需要历史上那版 `BUILD_QDLDL` 补丁

## 依赖版本（详见依赖分析阶段报告）
- **qdldl v0.1.8**（强制·构建期·源码级）：上游 FetchContent 固定 `GIT_TAG v0.1.8`。
  osqp 以 `$<TARGET_OBJECTS:qdldlobject>` 内联编译 qdldl（`algebra/builtin/CMakeLists.txt:21`、
  `CMakeLists.txt:413/432`），并把 `qdldl.c`/`qdldl.h` 打进 `share/osqp/codegen_files/`
  代码生成资源包 —— 故必须是**源码**依赖；已发布的 `qdldl/0.1.8` 二进制包只提供
  `libqdldl.a` + 头文件（实测包内容清单），无法满足该消费语义。配方用官方 tarball
  固定 sha256 离线喂给 FetchContent，`requires` 保持为空。
- **Catch2 v2.13.6**（可选·仅测试）：`tests/CMakeLists.txt:40-43`；本机以官方源码离线提供。
  制品仓对应可消费版本为 `catch2/2.13.10-r0`（同 v2 API），配方构建单测 OFF 故不引用。
- 系统库：`libm`（`CMakeLists.txt:291` 对非 MSVC 恒定 `-lm`）；`-lrt -ldl` 仅在 `IS_LINUX`
  分支添加，OHOS 下 `IS_LINUX=OFF` 故不涉及（实测链接通过）。
- 宿主工具：CMake ≥3.18、clang、Python 3.12.9 + numpy 2.5.2 + scipy 1.18.0（仅测试数据生成）。
- 不启用：MKL / CUDA 代数后端（`OSQP_ALGEBRA_BACKEND` 默认 builtin）、
  `OSQP_PROFILER_ANNOTATIONS`（默认 OFF，显式钉住）——OHOS PC 无对应实现。

## R51 上游测试申报（清点 → 实跑 → 回填）
- 清点：`tests/` 子目录 21 个、`tests/**/CMakeLists.txt` 24 个、`add_test()` 注册 3 项、
  `TEST_CASE` 宏 72 处（Catch2 展开为 104 项用例）、`generate_problem.py` 13 个。
- 实跑环境：本机 OHOS/aarch64 原生构建，`OSQP_BUILD_UNITTESTS=ON`，
  Catch2/QDLDL 均为官方源码离线。
- 结果（**test_package 不替代上游测试统计**）：

| 测试程序（ctest 注册名） | 用例数 | 通过 | 失败 | 跳过 | 断言 |
|---|---|---|---|---|---|
| lin_alg_tester | 28 | 28 | 0 | 0 | 177 |
| osqp_tester | 38 | 38 | 0 | 0 | 539 |
| osqp_tester_custom_memory | 38 | 38 | 0 | 0 | 539 |
| **合计** | **104** | **104** | **0** | **0** | **1255** |

- 逐用例名称：`test_package/MANIFEST.yml`（3 个程序各 28/38/38 项全列）与
  `reports/test-report.md`；原始日志 `~/tttt/osqp-1.0.0-adapt/logs/step4-*.log`
- 配方 `build()` 未集成上游测试的技术原因：`tests/CMakeLists.txt:4-28` 在**配置期**即要求
  Python + numpy + scipy（缺失 `FATAL_ERROR`），CI 干净执行机不保证具备该组合；
  故上游测试在适配阶段独立构建全量实跑并如实登记。

## 验证结果
```bash
# 探索构建（打补丁后）
cmake --build build -j2                                  -> exit 0
ctest --test-dir build --output-on-failure               -> 100% tests passed, 0 failed out of 3 (exit 0)
./build/out/osqp_tester                                  -> All tests passed (539 assertions in 38 test cases) (exit 0)
./build/out/lin_alg_tester                               -> All tests passed (177 assertions in 28 test cases) (exit 0)
./build/out/osqp_tester_custom_memory                    -> All tests passed (539 assertions in 38 test cases) (exit 0)
cmake --install build --prefix $TEST_PREFIX              -> exit 0

# 配方（CI 同款 profile）
conan create archives/o/osqp/1.0.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=…            -> exit 0（静态，test_package 13/13 断言通过）
conan create … -o "osqp/*:shared=True"                                                     -> exit 0（共享，test_package 13/13 断言通过）
python3 scripts/ohc-run.py conan-verify osqp 1.0.0                                        -> exit 0，G0-G4 PASS，Verdict PASS
```
- 包内容（静态）：`include/osqp/*.h`(6) + `lib/libosqpstatic.a` + `share/osqp/codegen_files/**`
  （13 个 .c + 32 个 .h + Makefile）；`include/qdldl`、`lib/cmake` 已按配方裁剪。
- `libosqp.so` 的 `NEEDED` 仅 `libc.so` —— qdldl 目标文件确已内联，无外部线性库依赖。

## 交付物
| 文件 | 说明 |
|------|------|
| `conanfile.py` | Conan 配方（shared/fPIC；FetchContent 离线；裁剪 qdldl 头与 cmake 包描述） |
| `conandata.yml` | 双官方源（osqp + qdldl）URL/sha256 + 补丁声明（patches 段以版本为 key，L0f 合规） |
| `patches/0001-src-CMakeLists.txt.patch` | 唯一平台适配补丁（+2/-1，仅 osqp 自身文件） |
| `test_package/{conanfile.py,CMakeLists.txt,test.c,MANIFEST.yml}` | L1 消费者测试（13 项断言）+ 上游测试申报 |
| `reports/{conan-verify-report.md,test-report.md,conan-create.log}` | 验证证据 |
| `manifest.yaml` | 版本级元数据 |

> **归档原子性说明**：本目录只包含 osqp 自身的配方/补丁/测试/文档。QDLDL、Catch2 的源码
> **没有**被复制进归档（仅 conandata.yml 中声明官方 URL + sha256，构建期由 conan 下载到
> conan 缓存目录），也未引入任何依赖库的 recipe 或日志文件。

## 本地门禁复验（提交前）
```
W3 本地 CI（finish step5）      -> exit 0，.ci-result.json exit_code=0，log_sha256 a8b3de1d…
conan-verify（finish step4）    -> G0-G4 PASS，Verdict PASS
check-knowledge-gap（W5）       -> knowledge_count=7 unreferenced=0，✅ 通过（.knowledge-done）
PF1/PF2/PF3/PF4/PF5/PF6/PF7/PF8 -> ✅ PASS；PF9 手工同口径 ✅ PASS（共 0 findings）
git status -uall                -> 仅 13 个文件：archives/o/osqp/1.0.0/**(9) + knowledge/drafts/E606/E607(4)
交付文件本机绝对路径扫描         -> conanfile/conandata/patch/test_package 全部 0 处
```
> `reports/`、`packaging/`、`.ci-result.json`、`.staging-verified`、`.knowledge-done`、
> `ci-metadata.json` 均被仓库 `.gitignore` 覆盖（本机证据文件，不进 PR）；
> 因此上游测试统计已完整写入**受版本管理**的 `test_package/MANIFEST.yml` 与 `notes.md`。

## 注意事项
1. `osqp_GetVersion()` 在 v1.0.0 已改名 `osqp_version()`；消费方若参考 0.6.x 文档需调整。
2. 静态库产物名是 `osqpstatic`（上游 `OUTPUT_NAME`），共享库是 `osqp`；
   `package_info()` 按 `shared` 选项切换，消费方统一用 `osqp::osqp` target 即可。
3. `share/osqp/codegen_files/` 是代码生成功能（emosqp）的资源包，**不可裁剪**；
   裁掉的只有 `include/qdldl/*`（属 qdldl 包）与 `lib/cmake/*`（由 Conan 生成配置）。
4. 若日后要让 `conan create` 也跑上游测试，需先给 CI 执行机准备 python+numpy+scipy，
   并把 Catch2 换成制品仓的 `catch2/2.13.10-r0`（届时需 `test_requires` + 调整
   `tests/CMakeLists.txt` 的 FetchContent 段）。
---

**编译结束**: 2026-09-08 21:40
**最终状态**: built
