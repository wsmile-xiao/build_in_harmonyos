# DRAFT-matchit-r01-gtest-ohpcd-offline-run

> Contributor: junshi_liu | Status: Draft | Updated: 2026-09-02
> Source: matchit 1.0.0 HarmonyOS PC Path B adaptation (task matchit-1.0.0-r01-pc1-19-20260902T132357Z)
> 对应 KV: knowledge/drafts/DRAFT-matchit-r01-gtest-ohpcd-offline-run.kv

## 主题 / 触发场景

上游 C/C++ 库的测试套件以 `FetchContent`/`ExternalProject` 在 configure 期从
`github.com/google/googletest` 拉取 gtest 源码，而构建 worker 无法直连 GitHub
（`curl: Failed to connect to github.com port 443 ... timed out`），导致上游
测试无法按其原始 CMake 配置构建。gtest 已由 ohpcd registry 发布时（本基线
`gtest/1.17.0`），可用 Conan 制品直链完整编译并运行上游测试套件。

## 现象 / error_signature

```text
curl: (28) Failed to connect to github.com port 443 after 65263 ms: Couldn't connect to server
FetchContent: 无法拉取 googletest（github.com/google/googletest/archive/dcc92d0....tar.gz）
```

上游 cmake/FetchGTest.cmake：

```cmake
FetchContent_Declare(googletest
  GIT_REPOSITORY https://github.com/google/googletest.git
  GIT_TAG dcc92d0ab6c4ce022162a23566d44f673251eee4)
```

## 根因 / root_cause

worker 网络策略禁止直连 github.com；上游测试框架以 FetchContent 网络引导，
configure 期即失败。注意与 E342 的差异：E342 主路径为 `BUILD_TESTING=OFF`
放弃网络化上游测试；本候选在 **gtest 已由 ohpcd 发布** 的前提下，把 gtest
作为 Conan 制品引入，直链编译完整上游套件，**保留真实上游覆盖**（matchit 实测
78/78 PASS），且不注入配方网络依赖。

## 方案 / rec_approach

```bash
# 1) 从 ohpcd registry 获取 gtest 制品（头文件 + 静态库）
conan install --requires=gtest/1.17.0 -r=ohpcd \
  -pr:h=ci/conan/profiles/ohos-aarch64 --build=missing

# 2) 定位包内 include/lib
#    <conan2>/p/gtest*/p/include   libgtest_main.a libgtest.a libgmock*.a

# 3) 目标工具链直链编译上游用户测试源
/data/service/hnp/bin/clang++ -std=c++17 \
  -I include -I "$GT_INC" \
  test/matchit/app.cpp test/matchit/constexpr.cpp test/matchit/expr.cpp \
  test/matchit/legacy.cpp test/matchit/noRet.cpp test/matchit/id.cpp \
  test/matchit/ds.cpp \
  -L "$GT_LIB" -lgtest_main -lgtest -lpthread -o unittests

# 4) 运行
./unittests   # [==========] 78 tests from 7 test suites ran. [ PASSED ] 78 tests.
```

要点：

- 上游测试源不加修改、不断言删减、不开 `-Werror` 豁免之外的附加选项
- gtest 仅测试期使用：不入配方运行时 `requirements()`；header-only 包 build() 保持 no-op
- 上游套件结果计入全量通过率台账（matchit：78/78 = 100%），以本地运行证据回报

## 验证 / verification

```bash
./unittests
# [==========] 78 tests from 7 test suites ran. (7 ms total)
# [  PASSED  ] 78 tests.            run_exit=0
```

## 适用边界 / affected_scope

- 适用：上游测试以 FetchContent/ExternalProject 引导 googletest，且 ohpcd 已发布
  gtest 制品的 Conan 2 包（OHOS/Linux 交叉编译）——跨库可复用
- 不适用：gtest 未在 registry 发布，或上游测试依赖 gtest 之外的网络化框架
- 与 E342 的关系：E342 主路径为关闭网络化测试；本候选是其"离线依赖"方向的
  具体实现（已发布制品直链完整运行），不作废 E342

## 查重差异

- knowledge/doc/E342.md：命中同域；E342 只给通用方向，未沉淀"ohpcd 制品直链运行完整上游套件"路径
- knowledge/graph/index.tsv：E342 存在，E332 为原生 runner，均非本路径
- knowledge/drafts/：DRAFT-googletest-1.12.1-ohos-test-platform-constraints 讲 gtest 自身 OHOS
  运行约束（/tmp 只读等），主题不同
- 新增价值：无 GitHub 直连 worker 上不经网络引导保留完整上游测试覆盖的可行路径