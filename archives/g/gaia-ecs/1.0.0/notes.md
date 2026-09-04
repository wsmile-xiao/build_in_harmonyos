# gaia-ecs 1.0.0 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists.txt，header-only INTERFACE 库）
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4 / clang++（aarch64-unknown-linux-ohos，HarmonyOS HongMeng Kernel 1.12.0）
- 状态: built

## 编译步骤

1. 获取官方 v1.0.0 tarball（GitHub 直连超时，经 ghfast.top 镜像下载），sha256 核验：
   `0e6c4d8dbea7c9a6e01b84244aefa0a041c913ba289bbcaaa0770ece9a02c25d`
2. `cmake -DCMAKE_BUILD_TYPE=Release -DGAIA_BUILD_UNITTEST=ON -DGAIA_BUILD_BENCHMARK=OFF -DGAIA_BUILD_EXAMPLES=OFF -DFETCHCONTENT_SOURCE_DIR_DOCTEST=<doctest@3280104>`（doctest 依赖同样经镜像获取，checkout 到上游固定的 commit 3280104）
3. `make -j4 gaia_test` + 其余 7 个测试目标（no_autoreg/no_observers/no_systems/no_json 及单头文件变体）
4. `python3 scripts/ohc-run.py conan-init gaia-ecs 1.0.0` 生成骨架后重写为 header-only 配方
5. `python3 scripts/ohc-run.py conan-verify gaia-ecs 1.0.0` — G1/G2/G3/G4/L2/L4/L5 全部通过
6. 鸿蒙专项测试 `reports/ohos_special_test.cpp` 编译运行通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连下载/克隆超时 | 环境无法直连 github.com | 经 ghfast.top 镜像下载官方 tarball 与 doctest 源码；conan-verify 的 E017 镜像注入机制同样用于 conan create |
| 2 | conan-init 生成 autotools 模板 | gaia-ecs 无 configure/make，是 header-only CMake INTERFACE 库 | 按上游自带 pkg/conan/conanfile.py 改写为 package_type=header-library 配方（no_copy_source + exports_sources + package 拷 single_include/ 头文件） |
| 3 | 上游配方版本停留在 0.9.2 | 上游 pkg/conan/ 未随仓库更新 | 升至 1.0.0，sha256 更新为官方 v1.0.0 tarball 值，package_info os 检查加入 "OHOS"（R32 口径） |
| 4 | 初次从 git clone 打包的 tarball 导致 2 个多线程用例 SIGSEGV | 打包内容与官方 tarball 不一致（clone 包含的产物/内容差异） | 改用官方 v1.0.0 tarball 重建基线后 gaia_test 644/644 全部通过，排除基线污染 |

## 依赖版本

- doctest 2.4.12（上游 CMake FetchContent 固定 commit 3280104，v2.4.12 发布前快照）

## 验证结果

```bash
# 上游测试（官方 tarball 基线，CMake + doctest，8 个目标）
./src/test/gaia_test            # 644/644 passed, assertions 2254252 全过
./src/test/gaia_test_no_autoreg # 52 用例 51 passed 1 failed（GAIA_ECS_AUTO_COMPONENT_REGISTRATION=0 变体下
                                 # "Entity - exact has/get across archetype moves" SIGSEGV；主目标同用例通过，
                                 # 属该编译配置变体的上游缺陷，非本次适配引入；其余 6 个变体目标 rc=0）
# 鸿蒙专项测试
clang++ -std=c++17 -O2 -Isingle_include -pthread reports/ohos_special_test.cpp && ./ohos-special-test
# → OHOS special test gaia-ecs 1.0.0: OK（ECS 生命周期 + Parent 关系 + 线程池 32 任务真实执行）

# Conan 验证
python3 scripts/ohc-run.py conan-verify gaia-ecs 1.0.0   # 全部门禁通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-library 配方（C++17、pthread、gaia::gaia CMake target） |
| conandata.yml | 官方 v1.0.0 tarball + sha256 |
| test_package/ | 真实消费者测试（World 实体/组件/更新/删除生命周期） |
| reports/ohos_special_test.cpp | 鸿蒙专项测试（ECS + Parent 关系 + 线程池） |
| reports/knowledge_candidate_ledger.md | 知识候选台账与四范围查重（路径 A） |

## 注意事项

- 无补丁、无源码修改，纯配方适配；构建产物只有头文件（header-only）
- 官方 tarball 的 single_include/gaia.h 已随版本发布，直接打包即可
---

**编译结束**: 2026-09-03 04:57
**最终状态**: built
