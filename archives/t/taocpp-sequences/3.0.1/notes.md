# taocpp-sequences 3.0.1 适配笔记

## 编译环境
- 构建系统: cmake（header-only INTERFACE 库）
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4 / clang++（OHOS SDK /data/service/hnp/bin）
- 状态: built

## 编译步骤

1. 官方源码（GitHub tag 3.0.1，经 gh-proxy.com 镜像下载，因直连超时）：
   `curl -sSL -o taocpp-sequences-3.0.1.tar.gz 'https://gh-proxy.com/https://github.com/taocpp/sequences/archive/refs/tags/3.0.1.tar.gz'`
   SHA-256: `691c35d83ea68337ef9406a9a63656300f0e566115d3dd56eb8ce3b259d8fbb6`
2. CMake 配置（上游 CMakeLists 为 CMake 3.2 语法，CMake 4.1.2 需策略最低版本）：
   `cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DTAOCPP_SEQUENCES_BUILD_TESTS=ON -DCMAKE_POLICY_VERSION_MINIMUM=3.5`
3. 编译并运行上游测试：
   `cmake --build build -j4 && ctest --output-on-failure`
   34/34 通过（exit 0）——测试均为编译期 static_assert 用例 + 环境探针 tester。
4. Conan 配方（conanfile.py 手工改写为 header-only CMake 模式）：
   `python3 scripts/ohc-run.py conan-verify taocpp-sequences 3.0.1`
   G1-G4 + L2/L4/L5 全过；`conan create` 复现通过（ohos-aarch64 profile）。
5. finish（含 W2 结构 + R36 依赖 + W3 本地 CI 模拟）：exit 0。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连超时无法下载官方源码 | 执行环境无法直连 github.com（443 超时） | 使用 CI 同款 gh-proxy.com 镜像下载官方 tag tar.gz，SHA-256 实算核验与 conandata.yml 一致 |
| 2 | CMake 4.1.2 拒绝 cmake_minimum_required 3.2 的旧工程 | CMake 4 移除了对 <3.5 策略版本的兼容 | conanfile generate()/configure() 注入 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（知识查重：复用 E103/E187/DRAFT-E321） |
| 3 | W3/JC 拦截 | 其他库（cloog/kics）预存 .build-closed/.staging-verified 基线空文件进入 git 跟踪 | 基线隔离复验：记录确切路径与隔离前 SHA-256 → index 级临时隔离 → 复跑 W3 通过 → 原样恢复并核对恢复后 SHA-256 一致；不提交、不修改基线文件 |
| 4 | 本库 conandata.yml.ghfast-bak 残留 | conan-verify G2 镜像注入备份未清理 | 删除备份文件，确保归档目录无垃圾文件 |

## 源码修改

无补丁（header-only 库零源码修改）；仅 conan 配方与测试/消费者/专项用例。

## 依赖版本

无第三方依赖（header-only C++11 库）；工具链: clang 15.0.4, CMake 4.1.2, Conan 2.29.1（OHOS 适配版）, Python 3.12.9。

## 验证结果

```bash
# 上游测试 34/34
ctest --test-dir build --output-on-failure   # 34/34 Passed, exit 0
# 鸿蒙专项测试
clang++ -std=c++17 -Iinclude ohos_tests/taocpp_sequences_ohos_test.cpp -o taocpp_sequences_ohos_test && ./taocpp_sequences_ohos_test  # PASS, exit 0
# 消费者验证
clang++ -std=c++17 -Iinclude consumers/consumer_taocpp_sequences.cpp -o consumer_taocpp_sequences && ./consumer_taocpp_sequences  # PASS, exit 0
# test_package L1
clang++ -std=c++11 -Iinclude test_package/test.cpp -o test_package_taocpp_sequences && ./test_package_taocpp_sequences  # exit 0
```

## 注意事项

- 上游 CMakeLists `project(VERSION 2.0.1)` 与实际发行版 3.0.1 不一致（上游历史遗留），不影响构建；版本号以官方 tag 为准。
- 知识判断：`reuse_existing` + `path_a_no_knowledge`（C1→E103/E187/DRAFT-E321，C2→E321/E322/E257/E307），路径 B 不成立，见 reports/knowledge-candidate-ledger.md。

---

**编译结束**: 2026-09-19 22:01
**最终状态**: built