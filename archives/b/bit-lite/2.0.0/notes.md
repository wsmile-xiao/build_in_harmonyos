# bit-lite 2.0.0 适配笔记

## 编译环境
- 构建系统: cmake（header-only，CMake INTERFACE library）
- 编译日期: 2026-09-02
- 编译器: clang 15.0.4 / clang++（OHOS aarch64 profile）
- 状态: built（conan-verify G0-G4/L2/L4/L5 全通过）

## 编译步骤

1. init-build：下载官方 v2.0.0 tarball（GitHub release，SHA-256 已验证），生成 .work/.orig 双轨。
2. lang-preflight（R47）：判定 cpp，通过。
3. 上游测试构建（CMake + BIT_LITE_OPT_BUILD_TESTS=ON）：
   - cmake .. -DBIT_LITE_OPT_BUILD_TESTS=ON -DBIT_LITE_OPT_BUILD_EXAMPLES=OFF -DCMAKE_BUILD_TYPE=Release
   - make -> 生成 test-cpp98/11/14/17/20 五个变体
   - ctest -> 5/5 全部通过
4. conan-init + 重写配方（Conan 2.x header-only，参考 E321）：
   - conanfile.py: package_type=header-library, CMakeToolchain + OHOS 映射, BIT_LITE_OPT_BUILD_TESTS=ON
   - test_package: 真实调用 bit.hpp 核心 API 的消费者测试（R34，非空壳）
5. conan-verify：G0/G1/G2(conan create)/G3/G4 + L2/L4/L5 全部 PASS。
6. finish：W2 原子性检查通过（仅配方 9 文件）、W3 本地 CI 通过（L0/L1/L4/L5 全 pass，
   含 L1e 破坏性反向验证确认 test_package 真实依赖被测包；conan create 通过，
   .ci-result.json exit_code=0）、补丁归档完成。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试 cpp20 变体编译失败：`typedef redefinition with different types ('unsigned long long' vs 'unsigned long')`（bit.t.cpp:31） | C++20 下 `bit_USES_STD_BIT=1`（有 `<bit>`），bit.hpp 走 STD 分支，`bit_CPP11_90` 宏仅在该分支之外定义，预处理将其视为 0，bit.t.cpp 第 20 行落入 else 分支的 `typedef`，与系统 `<cstdint>` 已定义的 `uint64_t`（`unsigned long`）冲突 | 生成补丁 0001-test-bit.t.cpp.patch：第 20 行 `#if bit_CPP11_90` 改为 `#if bit_CPP11_OR_GREATER`（该宏全模式定义，C++20 下保持 `using std::uint64_t` 分支） |
| 2 | GitHub 下载超时 | 执行端网络无法直连 github.com | 通过 ghfast.top / gh-proxy.com 镜像下载官方 release archive，SHA-256 与 GitHub 内容一致 |
| 3 | W3 本地 CI 被 JC junk_check 拦截（embree/flatcv/goaccess 的 main 历史 junk 文件） | 分支无 commit 时 junk_check 回退 full 模式整仓扫描，命中其他库已提交到 main 的 .submit-state.json/.staging-verified/tarball；CI 侧 prdiff 模式只扫描 PR 文件，不受影响 | 先提交本库归档（incremental 模式只检查本库文件）后重跑 finish，W3 通过 |

## 源码修改

- patches/0001-test-bit.t.cpp.patch：修正上游测试 C++20 分支判断（bit_CPP11_90 → bit_CPP11_OR_GREATER）。
  属上游测试兼容性修复，已随 conandata.yml 声明，conan create 干净构建可复现。

## 依赖版本

- 无第三方运行时依赖（header-only，零 requires）。
- 工具链：clang 15.0.4、cmake 4.1.2、Conan 2.29.1。

## 验证结果

- conan-verify：G0-G4 + L2/L4/L5 全 PASS（conan create 通过，test_package 运行通过）。
- W3 本地 CI：L0_RESULT=pass, L1_RESULT=pass, L4_RESULT=pass, L5_RESULT=pass；1/1 包成功，通过率 100%。
- 上游测试 ctest：5/5 变体全部通过（cpp98/11/14/17/20），耗时 <1s。
- 路径判断：路径 A（依赖项基础适配），复用 E321 知识（martinmoene/nonstd-lite 系 Conan 2.x header-only 迁移），
  本库无新增跨库通用知识；PR 前缀按任务要求为 【依赖项】。

## 上游测试台账

- 测试源：test/bit.t.cpp（22 个独立 CASE）+ test/bit-main.t.cpp（6 个 CASE：版本/配置/语言特性），框架 lest（test/lest/lest_cpp03.hpp，第三方单头测试框架，非测试用例）。
- 测试构建：test/CMakeLists.txt 生成 bit-lite-cpp98/11/14/17/20.t 五个可执行，CTest 注册 test-cpp98..cpp20 共 5 项。
- 样例/基准/fixture：example/01-basic.cpp 为示例（非独立用例，不在上游测试集内）；无基准/fixture。
- 全量口径：独立上游用例 = 22（bit.t.cpp 的 CASE），按 5 个语言标准变体实际运行；
  22/22 全部通过（5 变体 × 22 = 110 次执行全部断言通过）。
- bit-main.t.cpp 中 6 个 CASE 为元信息/语言特性展示（[.bit][.version] 等带点号隐藏标签），
  计入台账但不计入 bit.t.cpp 的 22 个独立功能用例分母。

## 知识候选台账与查重

- 候选 1：nonstd-lite 系（martinmoene）header-only 库 Conan 2.x 迁移——查重：knowledge/graph/E321
  （byte-lite/any-lite/span-lite 同族条目）完全覆盖，直接复用，无新增差异。
- 候选 2：bit.t.cpp C++20 分支宏判断修复——查重：index.tsv 中 E091/E119（sockaddr redefinition，
  网络头冲突）不相关；E321 未覆盖（问题在上游测试分支选择）；drafts/ 无相同签名条目。
  判定：该问题是 bit-lite 上游测试的 C++20 兼容性特例，修复仅为单点宏调整，
  不具备跨库可复用知识价值，不建立新草稿；路径 A 决定不受影响。
- 路径决定：任务类型为依赖项（initial_pr_prefix 【依赖项】），本库完整复用 E321 知识，
  无新增跨库通用知识 → 路径 A（常规基础适配），PR 前缀 【依赖项】。

## 注意事项

- bit.hpp 在 C++20（std::bit 可用）与 C++17- 环境下宏定义分支不同，后续该家族库
  （byte-lite/span-lite 等）若升级支持 C++20 需留意测试的 bit_*_90 系列宏引用。
- W3 本地 CI 在分支无 commit 时会回退 full 模式整仓扫描，命中 main 历史其他库 junk；
  正式 CI 用 prdiff 模式不受影响（本次已通过提交归档规避）。

---

**编译结束**: 2026-09-02 22:58
**最终状态**: built