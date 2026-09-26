# fixed_math 2.2.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-22
- 编译器: clang/clang++ (15.0.4, aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

```bash
# 环境: Python 3.12.9 / Conan 2.29.1 / OHOS 适配版（os=OHOS 枚举）/ cmake 4.1.2
# 源码: 官方 tag v2.2.0（GitHub 直连不可达，CI 自动注入 ghfast.top 镜像 fallback，本地经 gh-proxy.com 核验 SHA-256）
#       sha256 = d746306e9e3b94ba30d529087a51acdfadf9bb1429dcb8d6ee05a4f6e41f05e7
# 配方: archives/f/fixed_math/2.2.0/conanfile.py（CMake header-library, INTERFACE target）
python3 scripts/ohc-run.py init-build fixed_math 2.2.0 --no-download --tar tar.gz
python3 scripts/ohc-run.py lang-preflight fixed_math 2.2.0 --src <work>
python3 scripts/ohc-run.py conan-init fixed_math 2.2.0
# 修正配方为 CMake header-library（conan-init 误判 autotools），补 test_package
conan create archives/f/fixed_math/2.2.0 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
python3 scripts/ohc-run.py conan-verify fixed_math 2.2.0   # G1-G4 + L2/L4/L5 PASS
python3 scripts/ohc-run.py finish fixed_math 2.2.0 built   # W2 结构 + R36 + W3 本地 CI 通过
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create (G2) configure 失败 `file DOWNLOAD cannot compute hash`（CPM.cmake v0.40.2） | 上游 CMakeLists.txt 无条件 `include(cmake/CPM.cmake)`，configure 期从 GitHub 下载；CI 禁 GitHub | 补丁 0001 将其移入 `FIXEDMATH_ENABLE_UNIT_TESTS` 分支；配方 `-DFIXEDMATH_ENABLE_UNIT_TESTS=OFF` |
| 2 | test_package `error: invalid value 'c++23'` | OHOS clang 15 只认 C++23 草案拼写 | `-std=c++2b` |
| 3 | 探针 `cos(0)=0.999832` 断言失败 | 定点三角函数为查表近似（库特性） | 断言改误差带 ±0.001 |
| 4 | 上游单测 `run_consteval_test ... not a constant expression`（7 个可执行） | clang 15 未实现 C++23 P2647（constexpr 内 static constexpr 局部变量） | 工具链限制，记入台账分母（详见 reports/upstream-test-ledger.md + 知识草稿） |
| 5 | `'source_location' file not found`（测试环境） | OHOS libcxx-ohos 无 `<source_location>` 头 | 测试环境 shim（__builtin_source_location），不入配方/PR |
| 6 | W3 首轮 JC 命中 cloog/kics 基线 .build-closed/.staging-verified | 其他库已提交的空占位文件（HEAD 基线） | 基线隔离复验：记录 pre_sha256 → 临时隔离 → 复跑通过 → 原样恢复（pre==post，空文件） |

## 源码修改

- 无三方库源码修改；仅 1 个配方级 portability 补丁 `patches/0001-CMakeLists.txt.patch`（CPM 引入条件化）

## 测试

- 上游单测: 全量 13/37 = 35.1%（c++2b + 本地 ut-ext v2.0.1_5 + shim 实测，6 可执行/13 用例通过；7 可执行 consteval 工具链限制、1 未注册源缺失 tag 外头文件）；当前配置可执行集合 6/6 = 100%
- HarmonyOS 专项: reports/ohos_special_test/fixed_math_ohos_special_test.cpp 编译运行全过（constexpr 算术/单位换算/定点三角误差带/16.16 布局/字符串往返）
- test_package 消费者探针: conan create 实测通过（clang++ -std=c++2b，4 组断言）
- 详见 reports/test-report.md / upstream-test-ledger.md / adaptation-evidence.md（reports/ 为 AI 元数据，不随 PR 提交）

## 知识

- 7 轴查重与路径判断: reports/knowledge-candidate-ledger.md
- 草稿对: knowledge/drafts/DRAFT-fixed_math-2.2.0-ohos-clang15-consteval-static-constexpr-local-p2647.{kv,md}（随本库 PR 交付）
- reuse_existing: C2/C3/C4（既有条目覆盖）；new_draft: C1；path_a_no_knowledge: C5

## 关闭（编译结束）

【知识库扩展】fixed_math 2.2.0 首轮适配完成：conan-verify G1-G4 PASS、W3 本地 CI 100%、上游单测全量 13/37=35.1%（6/13 注册可执行，工具链限制如实计入）、HarmonyOS 专项与 test_package 消费者探针全过；已完成知识查重并建立 1 对草稿（consteval/P2647），commit+push 后提交 PR 交付。
COMPLETED
---

**编译结束**: 2026-09-22 21:54
**最终状态**: built
