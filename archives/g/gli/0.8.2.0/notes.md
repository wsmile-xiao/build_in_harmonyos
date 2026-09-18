# gli 0.8.2.0 适配笔记

## 编译环境
- 构建系统: cmake（header-only INTERFACE 库）
- 编译日期: 2026-09-17
- 编译器: clang 15.0.4 / clang++
- 状态: built（conan-verify 全部门禁通过）

## 编译步骤

```bash
# 1. 官方源码（GitHub release zip，SHA-256 a11067c7c457cfd0fb64fd330ce0308fbf222f731f6c8b500ebb6e69449fcc3f）
python3 scripts/ohc-run.py init-build gli 0.8.2.0 --url=https://github.com/g-truc/gli/releases/download/0.8.2.0/gli-0.8.2.0.zip --tar zip

# 2. 本地编译（CMake 4.1.2 需 CMAKE_POLICY_VERSION_MINIMUM=3.5 兼容上游 cmake_minimum_required 2.6）
cd $BUILD_SRC_DIR && mkdir build && cd build
cmake .. -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX
make -j2   # 0 错误，100%

# 3. 上游测试全量运行
ctest --output-on-failure -j2   # 70/70 通过

# 4. 鸿蒙专项测试
clang++ -std=c++0x -Wall -I. -I./external/glm -DSOURCE_DIR="$PWD" test/core/ohos_special.cpp -o build/test-ohos-special
./build/test-ohos-special   # 20/20 断言通过

# 5. Conan 配方生成与验证
python3 scripts/ohc-run.py conan-init gli 0.8.2.0
python3 scripts/ohc-run.py conan-verify gli 0.8.2.0   # G1-G4 + L2/L4/L5 全部 PASS

# 6. 收尾（W2/W3）
python3 scripts/ohc-run.py finish gli 0.8.2.0 published
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.1.2 拒绝 `cmake_minimum_required(VERSION 2.6)` | CMake 4.x 移除 <3.5 兼容策略 | patches/0001-CMakeLists.txt.patch 提升为 3.5（E103 复用；CRLF 感知生成） |
| 2 | 消费者编译 `'glm/glm.hpp' file not found` | gli 公开头内置依赖 GLM 0.9.8（external/glm） | conanfile.py package() 随包分发 vendored GLM 头到 include/glm（路径 B 草稿） |
| 3 | `test/core/core_convert.cpp:35` ordered comparison between pointer and zero | 2016 旧代码 `strstr(...) > 0` 指针有序比较 | 改为 `!= NULL`（路径 B 草稿） |
| 4 | test_package 断言 size 不符 | `texture2d(Format, Extent)` 双参构造生成完整 mipmap 链，size() 为全层级之和 | 显式单层级构造 `texture2d(Format, Extent, 1)` |

## 源码修改

- patches/0001-CMakeLists.txt.patch：`cmake_minimum_required`/`cmake_policy` 2.6 → 3.5（CMake 4.x 兼容）

## 依赖版本

- 内置 GLM 0.9.8（vendored 于 external/glm，随包分发）
- 无外部 Conan 依赖（header-only）

## 验证结果

- 上游测试：70/70 ctest 全部通过（source_declared 73，configured_executable 70，3 个未注册旧文件 core_generate_mipmaps/core_load_gen/core_sampler2d）
- 鸿蒙专项测试：20/20 断言通过（test/core/ohos_special.cpp）
- 消费者用例：W3 L1 pass（test_package 编译链接运行 PASSED）
- conan-verify：G1-G4 + L2/L4/L5 全部 PASS
- W3 本地 CI：L0 pass / L1 pass / L4 pass / JC 基线隔离复验通过

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py + conandata.yml | header-only Conan 2 配方（package_type=header-library） |
| test_package/ | 消费者验证（find_package(gli) + gli::gli + 真实 API） |
| patches/0001-CMakeLists.txt.patch | CMake 4.x 兼容补丁 |
| reports/test-report.md | 上游测试双口径台账 + 鸿蒙专项 + 消费者 |
| reports/knowledge-candidate-ledger.md | 知识候选台账与七轴查重（路径 B） |
| knowledge/drafts/DRAFT-gli-0.8.2.0-headeronly-ship-bundled-dep-headers.{md,kv} | 路径 B 草稿 1 |
| knowledge/drafts/DRAFT-gli-0.8.2.0-strstr-pointer-compare-clang15.{md,kv} | 路径 B 草稿 2 |

## 注意事项

- 上游 CMakeLists 为 CRLF 行尾，补丁必须 CRLF 感知生成（git apply 校验）
- gli 无 CLI 产物（header-only），不创建 commands.json（R38 库类型豁免）
- W3 首次命中其他库 cloog 基线文件（.build-closed/.staging-verified），已按基线隔离复验：记录 SHA-256、临时隔离、复跑门禁通过、原样恢复且 SHA 一致，未纳入 PR

---

**编译结束**: 2026-09-17
**最终状态**: built
**路径决定**: path_b（知识库扩展）