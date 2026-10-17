# sexpp 0.9.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-16
- 编译器: clang/clang++ (15.0.4)
- 状态: built

## 编译步骤

```bash
# 官方 tag 源码: https://github.com/rnpgp/sexpp v0.9.1 (tar.gz sha256 3cd80b05...d8fe)
# 本地构建 (worktree):
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DDOWNLOAD_GTEST=OFF \
      -DCMAKE_PREFIX_PATH=$HOME/usr/local -DCMAKE_INSTALL_PREFIX=$HOME/usr/local
make -C build -j2            # libsexpp.a + sexpp-cli + sexpp-tests
# 上游测试 (82 个 TEST，最小补丁纳入 traits-tests.cpp 后全部实例化):
./build/bin/sexpp-tests --gtest_filter='-ExceptionTests.SexpWarning:G23ExceptionTests.G23Warning'
# Conan 配方: conan-init 修正为 CMake 模板 (init-build 误判 autotools)
python3 scripts/ohc-run.py conan-verify sexpp 0.9.1   # 8 门禁 PASS
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-init 生成 autotools 配方 | init-build 按 URL 猜测构建系统为 autotools，实际是 CMake | 用 CMake 模板重写 conanfile.py（DOWNLOAD_GTEST=OFF + WITH_SEXP_TESTS=OFF 避免 FetchContent 网络） |
| 2 | 上游测试 70/82 实例化 | traits-tests.cpp（12 个 TEST）在 v0.9.1 与 master 的 CMake add_executable 均未列出 | 最小补丁将 traits-tests.cpp 纳入 sexpp-tests 目标，实测 12/12 通过 |
| 3 | 2 个用例 SIGABRT | GTest CapturedStream 非 Android/iOS 分支硬编码 `/tmp/`（gtest-port.cc:1090），OHOS /tmp 为 erofs 只读；TMPDIR/TMP/TEMP 环境变量无效 | 平台阻塞记录（计入分母不计通过），提供完整首错/命令/恢复条件 |
| 4 | 测试输入 "(hello (world 42))" 解析失败 | sexpp 语法中数字 token 需引号形式（`"42"`），裸数字 token 在列表内报 illegal character ')' | test_package 改用 `(hello (world "42"))` |
| 5 | conandata.yml sha256 占位符 | conan-init 模板未回填 | 填入官方 tarball 真实 sha256: 3cd80b05b9254945664d4c3bcf9d88c568a0c5087d8dd33a034335d19291d8fe |
| 6 | commands.json 缺失 (R38) | 构建产物含 CLI (bin/sexpp) | 创建 archives/s/sexpp/commands.json 声明 tool 类型 |

## 源码修改

- `0001-CMakeLists.txt.patch`: sexpp-tests 目标纳入 `tests/src/traits-tests.cpp`（上游遗漏的上游测试入口，最小补丁）
- `archives/s/sexpp/commands.json`: CLI 声明（R38）

## 依赖版本

- googletest 1.14.0（系统安装，`find_package(GTest)`；CI 侧配方 DOWNLOAD_GTEST=OFF）
- 无其他 Conan 运行时依赖（纯 C++11 单库）

## 验证结果

```bash
# 上游测试全量通过率: 80/82 = 97.6% (当前配置可执行集合 80/80 = 100%)
./build/bin/sexpp-tests --gtest_filter='-ExceptionTests.SexpWarning:G23ExceptionTests.G23Warning'  # exit 0, 80 PASS
# HarmonyOS 专项测试: 4/4 PASS (canonical roundtrip / base64 / illegal input / depth limit)
# 消费者用例: exit 0 (解析+canonical 回打)
# conan-verify: G0-G4/L2/L4/L5 全 PASS
# W3 本地 CI: L0/L1/L4/L5 pass, 1/1 包通过, L1e 破坏性反向验证通过
```

## 知识候选台账与查重（路径判断依据）

任务类型: 知识库扩展（候选观察）

### 候选 1: GTest CapturedStream 硬编码 /tmp，OHOS 只读 /tmp 下 CaptureStdout 用例 SIGABRT
- **真实错误**: `gtest-port.cc:1102 Failed to create tmp file /tmp/gtest_captured_stream.XXXXXX` → `gtest-port.cc:1126 FATAL` → SIGABRT (exit 134)
- **根因**: GTest 1.14 CapturedStream 在非 Android/iOS 分支硬编码 `/tmp/`（不读 TMPDIR/TMP/TEMP）；OHOS `/tmp` 挂载为 erofs 只读
- **修复**: 环境变量无法覆盖（GTest 不读）；需可写 /tmp 或 GTest 源码补丁支持 TMPDIR。专用临时目录 + TMPDIR 注入实测仍失败
- **验证**: 2 个用例（ExceptionTests.SexpWarning、G23ExceptionTests.G23Warning）在专用临时目录 + TMPDIR/TMP/TEMP 注入下仍 SIGABRT；其余 80 用例不受影响
- **适用范围**: 所有使用 GTest CaptureStdout/CaptureStderr 的上游测试在 OHOS 只读 /tmp 环境下的库
- **查重（四范围）**:
  - E002 (set-env-var TMPDIR): trigger_overlap（/tmp 只读）但 solution 不适用（GTest 不读 TMPDIR）
  - E265 (fatsort TMPDIR/FS_IMG 覆盖): trigger_overlap（/tmp erofs）solution_overlap（TMPDIR 方案），但 fatsort 测试脚本读 TMPDIR，GTest 硬编码 → 不同触发路径
  - DRAFT-ohos-check-framework-temp-env-not-tmpdir: trigger_overlap（只读 /tmp 下测试框架）solution_overlap（临时目录环境变量），但 check 框架读 TEMP、GTest 捕获流读任何变量均无效 → boundary_novelty
  - 其余 /tmp 条目（E011/E052/E060/E136/E363/E461/E292/E302）: 均为 configure/config.status/shell/其他框架，与本候选无 causal 重复
- **七轴**: exact_duplicate=false, causal_duplicate=false, trigger_overlap=true（E002/E265/DRAFT-check-temp）, solution_overlap=true（TMPDIR 系列）, combination_novelty=true（GTest 捕获流硬编码 × OHOS 只读 /tmp 组合无条目）, boundary_novelty=true（GTest CapturedStream 特例：无环境变量可覆盖）, test_migration_novelty=false
- **决定**: **new_draft**（新增 .md/.kv 配对草稿），路径 B

### 候选 2: traits-tests.cpp 源码存在但上游 CMake 未实例化
- **真实错误**: 无错误，双口径统计差异（source_declared 82 vs configured 70）
- **根因**: v0.9.1 与 master 的 CMakeLists add_executable(sexpp-tests) 均未列出 traits-tests.cpp（12 个 TEST 宏）
- **修复**: 最小补丁纳入 → 82/82 实例化，12/12 通过
- **适用范围**: 上游 tag 内测试文件未进构建目标的枚举恢复（流程通用规则已有 E292 类 CTest 迁移条目覆盖）
- **查重**: E292 (layered-ctest-migration) trigger_overlap（CTest 测试实例化），但本候选为单文件遗漏修复，通用恢复流程已由 SKILL 源码测试入口恢复规则覆盖
- **决定**: 不单独建草稿（流程规则已覆盖，属台账记录）

### 候选 3: conan-init 按 URL 误判构建系统
- **真实错误**: conan-init 生成 autotools 配方（实际 CMake 项目）
- **根因**: init-build/registry 按 URL 猜测 build_system，GitHub 仓库主页 URL 无特征
- **修复**: AI 核对 CMakeLists 后用 CMake 模板重写
- **适用范围**: 无通用知识价值（工具行为，AI 人工核对为常例）
- **决定**: 非知识候选（噪声）

## 路径判断结论

- **reuse_existing**: false（无 exact/causal 重复）
- **new_draft**: true → 候选 1 建立 DRAFT-sexpp-0.9.1-gtest-captured-stream-tmp-hardcode.{md,kv}
- **path_a_no_knowledge**: false
- 关系: 候选 1 与 DRAFT-ohos-check-framework-temp-env-not-tmpdir 为 similar_to（只读 /tmp 下测试框架临时目录，但变量解析链不同）；与 E002/E265 为 caused_by 基础（OHOS /tmp erofs 只读）

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py + conandata.yml + test_package/ | Conan 配方（CMake） |
| patches/0001-CMakeLists.txt.patch | traits-tests.cpp 纳入测试目标 |
| commands.json | CLI 声明 (R38) |
| reports/test-report.md | 双口径测试台账 + 平台阻塞详情 |
| reports/conan-verify-report.md | 8 门禁验证报告 |
| notes.md | 本笔记（含知识候选台账） |

## 注意事项

- OHOS /tmp 为 erofs 只读：GTest CaptureStdout/CaptureStderr 用例会 SIGABRT（GTest 硬编码 /tmp 不读 TMPDIR），属真实平台阻塞，恢复条件见 test-report.md
- 数字 token 在 sexpp 输入中需引号形式（`"42"`），裸数字在嵌套列表内报非法字符
---

**编译结束**: 2026-09-17 17:29
**最终状态**: built
